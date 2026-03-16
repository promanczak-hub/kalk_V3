import asyncio
from sqlalchemy import select
from core.database import async_session_maker
from models.kalkulacje import LTRKalkulacja
from api.kalkulacje.services.ltr_runner import execute_ltr_pipeline

async def main():
    calculation_id = "7f742aba-24be-426d-9999-1fbf7a41a6be"
    async with async_session_maker() as session:
        result = await session.execute(select(LTRKalkulacja).where(LTRKalkulacja.id == calculation_id))
        kalk = result.scalar_one_or_none()
        if not kalk:
            print("Kalkulacja not found")
            return
            
        params = {
            "okres_mc": 36,
            "przebieg_roczny": 50000,
            "wplyw_na_wr_mc": 0
        }
        res = await execute_ltr_pipeline(session, kalk, params)
        print("====== WYNIKI V3 ======")
        print(f"Cena zakupu BUDZET: {res.cena_zakupu.CenaZakupu:.2f}")
        print(f"Cena zakupu bez opon: {res.cena_zakupu.CenaZakupuBezOpon:.2f}")
        print(f"Cena 1 kpl. opon (tires_capex_net): {res.cena_zakupu.tires_capex_net:.2f}")
        
        print(f"Opony MC: {res.opony.RataOpon:.2f}")
        print(f"Ilosc kompletow opon na kontrakt: {res.opony.IloscOpon:.2f}")
        print(f"Baza opon capex_tires: {res.opony.tires_capex_net:.2f}")
        
        print(f"Koszty dodatkowe: {res.koszty_dodatkowe.RataKosztowDodatkowych:.2f}")
        print(f"Ubezpieczenie: {res.ubezpieczenie.RataUbezpieczenia:.2f}")
        print(f"Samochod zastepczy: {res.samochod_zastepczy.RataSamZastepczy:.2f}")
        print(f"WR: {res.utrata_wartosci.WartoscRezydualnaNaKoniec:.2f}")
        print(f"WR %: {(res.utrata_wartosci.WartoscRezydualnaNaKoniec/res.utrata_wartosci.podstawa_liczenia_v1)*100 if getattr(res.utrata_wartosci, 'podstawa_liczenia_v1', 0) else 0:.2f}%")
        print(f"Czynsz Finansowy: {res.finanse.CzynszFinansowy:.2f}")
        print(f"Czynsz Techniczny: {res.finanse.CzynszTechniczny:.2f}")
        print(f"Stawka Laczna: {res.stawka.OferowanaStawka:.2f}")
        print(f"Koszt dzienny: {res.koszt_dzienny.KosztDziennyNetto:.2f}")

if __name__ == "__main__":
    asyncio.run(main())
