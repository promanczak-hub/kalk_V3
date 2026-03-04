import { LayoutList, Eye, EyeOff } from "lucide-react";

interface EquipmentToggleSectionProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  categories: any[];
  hiddenItems: Set<string>;
  onToggleItem: (catIndex: number, itemIdx: number) => void;
}

export function EquipmentToggleSection({ categories, hiddenItems, onToggleItem }: EquipmentToggleSectionProps) {
  if (!categories || categories.length === 0) return null;

  return (
    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
      <h3 className="font-semibold text-slate-800 flex items-center mb-1">
        <LayoutList className="w-4 h-4 mr-2 text-emerald-500" /> Wyposażenie
      </h3>
      <p className="text-xs text-slate-500 mb-5">
        Kliknij w elementy, których nie chcesz umieszczać na końcowym wydruku PDF.
      </p>
      
      <div className="space-y-4">
        {categories.map((cat: { category_name: string; items: string[] }, catIdx: number) => (
          <div key={catIdx} className="border border-slate-100 rounded-lg p-3 bg-slate-50/50">
            <h4 className="font-medium text-slate-700 text-sm mb-2 px-1">{cat.category_name}</h4>
            <div className="flex flex-wrap gap-2">
              {cat.items?.map((item: string, itemIdx: number) => {
                const isHidden = hiddenItems.has(`${catIdx}-${itemIdx}`);
                return (
                  <button
                    key={itemIdx}
                    onClick={() => onToggleItem(catIdx, itemIdx)}
                    className={`inline-flex items-center text-[11px] px-2 py-1 rounded border transition-colors ${
                      isHidden 
                        ? "bg-slate-100 border-slate-200 text-slate-400 line-through opacity-60 hover:opacity-80" 
                        : "bg-white border-slate-200 text-slate-600 hover:border-emerald-300 hover:bg-emerald-50"
                    }`}
                  >
                    {isHidden ? <EyeOff className="w-3 h-3 mr-1.5" /> : <Eye className="w-3 h-3 mr-1.5 text-slate-400" />}
                    {item}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
