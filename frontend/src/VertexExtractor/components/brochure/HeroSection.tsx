import { useState, useRef } from "react";
import { ImagePlus, Trash2, Star, Sparkles, Loader2 } from "lucide-react";

export interface BrochureImage {
  id: string;
  url: string;
  isMain: boolean;
}

interface HeroSectionProps {
  images: BrochureImage[];
  setImages: React.Dispatch<React.SetStateAction<BrochureImage[]>>;
}

export function HeroSection({ images, setImages }: HeroSectionProps) {
  const [isProcessingAI, setIsProcessingAI] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newImages = Array.from(e.target.files).map(file => ({
        id: crypto.randomUUID(),
        url: URL.createObjectURL(file),
        isMain: images.length === 0 // Pierwsze dodane zdjęcie jest główne
      }));
      setImages(prev => [...prev, ...newImages]);
    }
  };

  const handleRemoveImage = (id: string) => {
    setImages(prev => {
      const filtered = prev.filter(img => img.id !== id);
      // Jeśli usunęliśmy główne, przypisz nowe główne pierwszemu na liście
      if (filtered.length > 0 && !filtered.some(img => img.isMain)) {
        filtered[0].isMain = true;
      }
      return filtered;
    });
  };

  const setMainImage = (id: string) => {
    setImages(prev => prev.map(img => ({
      ...img,
      isMain: img.id === id
    })));
  };

  const processWithNanoBanana = async (id: string) => {
    setIsProcessingAI(true);
    // Symulacja wywołania API NanoBanana (odszumianie/wycinanie tła)
    console.log(`Zlecono obróbkę NanoBanana dla obrazka: ${id}`);
    setTimeout(() => {
      setIsProcessingAI(false);
      alert("NanoBanana AI: Funkcja w przygotowaniu! W przyszłości wytniemy tło lub je zgenerujemy od nowa.");
    }, 2000);
  };

  return (
    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-slate-800 flex items-center">
          <ImagePlus className="w-4 h-4 mr-2 text-indigo-500" /> Zdjęcia pojazdu
        </h3>
        <button 
          onClick={() => fileInputRef.current?.click()}
          className="text-xs font-medium bg-slate-100 text-slate-700 hover:bg-slate-200 px-3 py-1.5 rounded-lg flex items-center transition-colors"
        >
          <ImagePlus className="w-3.5 h-3.5 mr-1.5" /> Dodaj zdjęcie
        </button>
        <input 
          type="file" 
          multiple 
          accept="image/*" 
          className="hidden" 
          ref={fileInputRef}
          onChange={handleFileChange}
        />
      </div>

      <p className="text-xs text-slate-500 mb-4">
        Wgraj zrzuty ekranu oferty dealera lub gotowe zdjęcia. Użyj sztucznej inteligencji, aby wyczyścić z tła zbędne obiekty i ułatwić formatowanie.
      </p>

      {images.length === 0 ? (
        <div className="border-2 border-dashed border-slate-200 rounded-lg p-8 flex flex-col justify-center items-center bg-slate-50/50 text-slate-400">
           <ImagePlus className="w-8 h-8 mb-2 opacity-50" />
           <p className="text-sm">Brak wgranych zdjęć.</p>
           <button onClick={() => fileInputRef.current?.click()} className="mt-3 text-xs text-indigo-600 font-medium hover:underline">Wybierz z dysku</button>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {images.map(img => (
            <div key={img.id} className={`relative group rounded-xl border-2 overflow-hidden transition-all ${img.isMain ? 'border-indigo-500 ring-2 ring-indigo-500/20' : 'border-slate-200 hover:border-indigo-300'}`}>
              <img src={img.url} alt="Vehicle preview" className="w-full h-32 object-cover" />
              
              {/* Overlay with actions */}
              <div className="absolute inset-0 bg-slate-900/40 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-between p-2">
                 <div className="flex justify-between w-full">
                    {img.isMain ? (
                      <span className="bg-indigo-600 text-white text-xs uppercase font-bold px-2 py-0.5 rounded shadow-sm flex items-center">
                        <Star className="w-3 h-3 mr-1 fill-current" /> Główne
                      </span>
                    ) : (
                      <button 
                         onClick={() => setMainImage(img.id)}
                         className="bg-white/90 text-slate-700 text-xs uppercase font-bold px-2 py-0.5 rounded shadow-sm hover:bg-white flex items-center"
                      >
                        Ustaw jako główne
                      </button>
                    )}
                    <button 
                      onClick={() => handleRemoveImage(img.id)}
                      className="bg-red-500/90 text-white p-1 rounded hover:bg-red-600 shadow-sm"
                      title="Usuń zdjęcie"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                 </div>
                 
                 <button 
                   onClick={() => processWithNanoBanana(img.id)}
                   disabled={isProcessingAI}
                   className="w-full bg-gradient-to-r from-violet-600/90 to-indigo-600/90 hover:from-violet-500 hover:to-indigo-500 text-white text-xs font-medium py-1.5 rounded flex items-center justify-center shadow-sm disabled:opacity-50"
                 >
                   {isProcessingAI ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Sparkles className="w-3 h-3 mr-1" />}
                   Clean Background (NanoBanana)
                 </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
