import { get, post } from "@/core/api/client";

const API = "educore.api.v1.timetable";

/** who reads timetables (educore.api.v1.timetable.READ_ROLES) */
export const TIMETABLE_ROLES = [
  "Timetable Officer", "System Manager", "Facilities Manager", "Head of Department", "Dean", "Faculty Officer", "Registrar",
  "Registry Officer", "Campus Director", "Examinations Officer", "Executive Management",
];

export interface Slot {
  name: string;
  student_group: string;
  course: string;
  code: string;
  course_name: string;
  campus: string;
  academic_year: string;
  semester: string;
  day: string;
  start_time: string;
  end_time: string;
  room: string;
  room_name: string;
  kind: string;
  lecturers: string[];
}

export interface Room {
  name: string;
  room_name: string;
  room_number: string | null;
  seating_capacity: number;
  room_type: string;
  disabled: boolean;
}

export interface TimetableClass {
  group: string;
  code: string;
  course_name: string;
  runs: string;
  students: number;
  lecturers: string[];
  hours: number;
}

export interface TimetablePage {
  campus: string | null;
  campuses: string[];
  academic_year: string | null;
  academic_years: string[];
  semester: string;
  semesters: string[];
  days: string[];
  kinds: string[];
  room_types: string[];
  slots: Slot[];
  classes: TimetableClass[];
  rooms: Room[];
  can_edit: boolean;
  can_edit_rooms: boolean;
}

export type SlotInput = Partial<Pick<Slot, "name">> & Pick<Slot, "student_group" | "semester" | "day" | "start_time" | "end_time" | "room" | "kind">;
export type RoomInput = Partial<Pick<Room, "name">> & Omit<Room, "name"> & { campus: string };

export const timetablePage = (params: { campus?: string | null; academic_year?: string | null; semester?: string | null }) =>
  get<TimetablePage>(`${API}.page`, Object.fromEntries(Object.entries(params).filter(([, v]) => v)) as Record<string, string>);
export const saveSlot = (slot: SlotInput) => post<{ page: TimetablePage; warnings: string[] }>(`${API}.save_slot`, { slot });
export const deleteSlot = (name: string) => post<TimetablePage>(`${API}.delete_slot`, { name });
export const saveRoom = (room: RoomInput) => post<Room[]>(`${API}.save_room`, { room });
export const myWeek = () => get<{ academic_year: string | null; semester: string; slots: Slot[] }>(`${API}.mine`);
