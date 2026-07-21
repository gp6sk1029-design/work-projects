export type Attendee = {
  id: number;
  dept: string;
  name: string;
  rank: string;
  fee: number;
  support: number;
  due: number;
  alcohol: string;
  shuttle: string;
  note: string;
  arrived: number; // 0/1
  paid: number; // 0/1
};

export const SELECT_ATTENDEES = `SELECT id, dept, name, rank, fee, support, due, alcohol, shuttle, note, arrived, paid
   FROM attendees ORDER BY id`;
