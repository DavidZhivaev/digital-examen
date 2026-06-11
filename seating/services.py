import io
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from typing import List, Dict, Any, Tuple
from users.models import User
from rooms.models import Room
from classes.models import SchoolClass, StudentClassHistory


class SeatingService:
    @staticmethod
    def _get_row_letter(row_idx: int) -> str:
        string = ""
        while row_idx > 0:
            row_idx, remainder = divmod(row_idx - 1, 26)
            string = chr(65 + remainder) + string
        return string

    @staticmethod
    async def prepare_data(person_ids: List[str], room_ids: List[int], teacher_ids: List[str]) -> Dict[str, Any]:
        students = await User.filter(person_id__in=person_ids).prefetch_related("class_id")
        rooms = await Room.filter(id__in=room_ids)
        teachers = await User.filter(person_id__in=teacher_ids)
        
        class_ids = list(set([s.class_id for s in students if s.class_id]))
        classes = await SchoolClass.filter(id__in=class_ids)
        class_map = {c.id: c for c in classes}
        
        history = await StudentClassHistory.filter(user__person_id__in=person_ids)
        history_map = {}
        for h in history:
            history_map.setdefault(h.user_id, set()).add(h.school_class_id)

        return {
            "students": students,
            "rooms": rooms,
            "teachers": teachers,
            "class_map": class_map,
            "history_map": history_map
        }

    @classmethod
    async def validate_seating(cls, data: Dict[str, Any]) -> Tuple[bool, str, int, int]:
        total_students = len(data["students"])
        total_capacity = sum([r.rows * r.columns for r in data["rooms"]])
        
        if total_students > total_capacity:
            return False, "Недостаточно места в аудиториях", total_students, total_capacity
            
        if len(data["rooms"]) > len(data["teachers"]):
            return False, f"Недостаточно учителей. Нужно минимум {len(data['rooms'])}, дано {len(data['teachers'])}", total_students, total_capacity
            
        return True, "Успешно", total_students, total_capacity

    @classmethod
    def generate_seating_plan(cls, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        students = data["students"]
        rooms = sorted(data["rooms"], key=lambda r: (r.corpus, r.number))
        teachers = data["teachers"]
        class_map = data["class_map"]
        history_map = data["history_map"]

        students_by_class = {}
        for s in students:
            students_by_class.setdefault(s.class_id, []).append(s)

        corpus_capacities = {}
        for r in rooms:
            corpus_capacities[r.corpus] = corpus_capacities.get(r.corpus, 0) + (r.rows * r.columns)
            
        sorted_classes = sorted(students_by_class.items(), key=lambda x: len(x[1]), reverse=True)
        class_to_corpus = {}
        
        for class_id, cls_students in sorted_classes:
            allocated = False
            for corpus in sorted(corpus_capacities.keys(), key=lambda c: corpus_capacities[c], reverse=True):
                if corpus_capacities[corpus] >= len(cls_students):
                    class_to_corpus[class_id] = corpus
                    corpus_capacities[corpus] -= len(cls_students)
                    allocated = True
                    break
            if not allocated:
                best_corpus = max(corpus_capacities, key=corpus_capacities.get)
                class_to_corpus[class_id] = best_corpus
                corpus_capacities[best_corpus] -= len(cls_students)

        rooms_by_corpus = {}
        for r in rooms:
            rooms_by_corpus.setdefault(r.corpus, []).append(r)
            
        room_assignments = {r.id: [] for r in rooms}
        
        for class_id, cls_students in students_by_class.items():
            target_corpus = class_to_corpus.get(class_id)
            corp_rooms = rooms_by_corpus.get(target_corpus, [])
            if not corp_rooms:
                corp_rooms = rooms
                
            idx = 0
            for s in cls_students:
                attempts = 0
                while attempts < len(corp_rooms):
                    r = corp_rooms[idx % len(corp_rooms)]
                    max_cap = r.rows * r.columns
                    if len(room_assignments[r.id]) < max_cap:
                        room_assignments[r.id].append(s)
                        idx += 1
                        break
                    idx += 1
                    attempts += 1

        final_seating = []
        for r in rooms:
            room_students = room_assignments[r.id]
            grid = {}
            
            for s in room_students:
                best_seat = None
                min_penalty = float('inf')
                
                for row in range(1, r.rows + 1):
                    for col in range(1, r.columns + 1):
                        if (row, col) in grid:
                            continue
                            
                        penalty = 0
                        
                        neighbors = [
                            (row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1),
                            (row - 1, col - 1), (row - 1, col + 1), (row + 1, col - 1), (row + 1, col + 1)
                        ]
                        
                        for nr, nc in neighbors:
                            neighbor = grid.get((nr, nc))
                            if not neighbor:
                                continue
                                
                            is_same_desk = (nr == row) and (
                                (col % 2 == 1 and nc == col + 1) or (col % 2 == 0 and nc == col - 1)
                            )
                            
                            if is_same_desk:
                                if s.last_name == neighbor.last_name or (s.middle_name and s.middle_name == neighbor.middle_name):
                                    penalty += 100000
                                    
                            if s.class_id == neighbor.class_id:
                                penalty += 5000
                                
                            s_class_obj = class_map.get(s.class_id)
                            n_class_obj = class_map.get(neighbor.class_id)
                            if s_class_obj and n_class_obj and s_class_obj.corpus == n_class_obj.corpus:
                                penalty += 200
                                
                            s_hist = history_map.get(s.id, set())
                            n_hist = history_map.get(neighbor.id, set())
                            if s_hist & n_hist:
                                penalty += 1000

                        if s.sex is not None:
                            expected_parity = (row + col) % 2
                            actual_parity = 1 if s.sex == 1 else 0
                            if expected_parity != actual_parity:
                                penalty += 50

                        if penalty < min_penalty:
                            min_penalty = penalty
                            best_seat = (row, col)
                            
                if best_seat:
                    grid[best_seat] = s
            
            students_list = []
            for (row, col), s in grid.items():
                cls_obj = class_map.get(s.class_id)
                cls_name = cls_obj.display_name if cls_obj else "Неизвестен"
                fio = f"{s.last_name} {s.first_name}" + (f" {s.middle_name}" if s.middle_name else "")
                
                students_list.append({
                    "person_id": s.person_id,
                    "fio": fio,
                    "student_class": cls_name,
                    "seat": f"{cls._get_row_letter(row)}{col}"
                })
                
            final_seating.append({
                "room_id": r.id,
                "corpus": r.corpus,
                "number": r.number,
                "teachers": [],
                "students": students_list,
                "_raw_students": room_students
            })

        for item in final_seating:
            room_students = item["_raw_students"]
            best_teacher = None
            min_own_students = float('inf')
            
            for t in teachers:
                own_students_count = 0
                for s in room_students:
                    cls_obj = class_map.get(s.class_id)
                    if cls_obj and cls_obj.teacher_id == t.id:
                        own_students_count += 1
                
                if own_students_count < min_own_students:
                    min_own_students = own_students_count
                    best_teacher = t
            
            if best_teacher:
                t_fio = f"{best_teacher.last_name} {best_teacher.first_name}" + (f" {best_teacher.middle_name}" if best_teacher.middle_name else "")
                item["teachers"].append({"person_id": best_teacher.person_id, "fio": t_fio})

        return final_seating

    @classmethod
    def generate_excel(cls, seating_plan: List[Dict[str, Any]]) -> io.BytesIO:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Рассадка"
        
        font_header = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        font_body = Font(name="Arial", size=10)
        font_room = Font(name="Arial", size=12, bold=True, color="1F497D")
        
        fill_header = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
        fill_room = PatternFill(start_color="E9EDF4", end_color="E9EDF4", fill_type="solid")
        
        thin_border = Border(
            left=Side(style='thin', color='D9D9D9'),
            right=Side(style='thin', color='D9D9D9'),
            top=Side(style='thin', color='D9D9D9'),
            bottom=Side(style='thin', color='D9D9D9')
        )
        
        headers = ["ФИО", "Класс", "Место"]
        current_row = 1
        
        for room_data in seating_plan:
            ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=3)
            cell = ws.cell(row=current_row, column=1)
            teachers_str = ", ".join([t['fio'] for t in room_data['teachers']])
            cell.value = f"Корпус {room_data['corpus']} — Аудитория {room_data['number']} (Учителя: {teachers_str})"
            cell.font = font_room
            cell.fill = fill_room
            cell.alignment = Alignment(horizontal="left", vertical="center")
            ws.row_dimensions[current_row].height = 25
            current_row += 1
            
            for col_idx, h in enumerate(headers, 1):
                c = ws.cell(row=current_row, column=col_idx, value=h)
                c.font = font_header
                c.fill = fill_header
                c.alignment = Alignment(horizontal="center" if col_idx > 1 else "left")
            ws.row_dimensions[current_row].height = 20
            current_row += 1
            
            sorted_students = sorted(room_data["students"], key=lambda x: x["fio"])
            for s in sorted_students:
                ws.cell(row=current_row, column=1, value=s["fio"]).font = font_body
                ws.cell(row=current_row, column=2, value=s["student_class"]).font = font_body
                
                seat_cell = ws.cell(row=current_row, column=3, value=s["seat"])
                seat_cell.font = font_body
                seat_cell.alignment = Alignment(horizontal="center")
                
                for col_idx in range(1, 4):
                    ws.cell(row=current_row, column=col_idx).border = thin_border
                    
                ws.row_dimensions[current_row].height = 18
                current_row += 1
                
            current_row += 1 
            
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)
            
        file_stream = io.BytesIO()
        wb.save(file_stream)
        file_stream.seek(0)
        return file_stream