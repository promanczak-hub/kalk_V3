import { MessageSquareText } from "lucide-react";

interface NotesSectionProps {
  notes: string;
  onChange: (value: string) => void;
}

export function NotesSection({ notes, onChange }: NotesSectionProps) {
  return (
    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
      <h3 className="font-semibold text-slate-800 flex items-center mb-4">
        <MessageSquareText className="w-4 h-4 mr-2 text-amber-500" /> Notatki dla klienta (Opcjonalne)
      </h3>
      <div className="space-y-2">
        <p className="text-xs text-slate-500">
          Możesz wpisać dodatkowe informacje, które pojawią się na dole zunifikowanej broszury.
        </p>
        <textarea 
          value={notes}
          onChange={(e) => onChange(e.target.value)}
          placeholder="np. Samochód dostępny od ręki. Możliwość finansowania w promocyjnym leasingu 103%..."
          className="w-full text-sm p-3 border border-slate-200 rounded-md focus:ring-2 focus:ring-amber-500 focus:outline-none min-h-[100px] resize-y"
        />
      </div>
    </div>
  );
}
