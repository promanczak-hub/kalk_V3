"use client";

export function Header() {
  return (
    <>
      <div className="flex flex-col mb-12 relative">
        <div className="flex justify-between items-start">
          <img
            src="/express-logo.png"
            alt="Express Car Rental"
            className="h-12 md:h-14 w-auto mb-4 object-contain"
          />
        </div>
        <h1 className="text-3xl tracking-tight font-light text-slate-800 mb-2">
          Platforma Ekstrakcji Danych
        </h1>
        <p className="text-sm text-slate-500 max-w-2xl font-normal leading-relaxed">
          Wgraj broszurę PDF lub cennik XLSX. Sztuczna inteligencja zekstrahuje
          konfigurację pojazdu i utworzy ustandaryzowany plik JSON.
        </p>
      </div>
    </>
  );
}
