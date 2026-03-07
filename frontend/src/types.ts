export interface V1FactoryOption {
  Id: number;
  Nazwa: string;
  CenaNetto: number;
  Cena: number;
  isNierabatowany: boolean;
  WR: boolean;
}

export interface V1ServiceOption {
  Id: number;
  Nazwa: string;
  CenaNetto: number;
  Cena: number;
  isNierabatowany: boolean;
  WR: boolean;
}

export interface V1FinancialComponent {
  Wartosc?: number;
  RozkladMarzy?: number;
  KwotaMarzy?: number;
  KosztPlusMarza?: number;
  RozkladMarzyKorekta?: number;
  KwotaMarzyKorekta?: number;
  KosztPlusMarzaKorekta?: number;
}

export interface V1GlownyMatrixParameters {
  LacznyKosztCzesciOdsetkowejRaty?: V1FinancialComponent;
  UtrataWartosci?: V1FinancialComponent;
  OkresUzytkowania?: number;
  LacznieUbezpieczenie?: V1FinancialComponent;
  KosztTechnicznySamochodZastepczy?: V1FinancialComponent;
  KosztTechnicznySerwis?: V1FinancialComponent;
  KosztTechnicznyOpony?: V1FinancialComponent;
  KosztyDodatkowe?: V1FinancialComponent;
  CzynszFinansowyRazem?: V1FinancialComponent;
  CzynszTechnicznyRazem?: V1FinancialComponent;
  KosztRazem?: V1FinancialComponent;
  KosztFinansowy?: V1FinancialComponent;
  KosztTechniczny?: V1FinancialComponent;
  KosztUbezpieczenie?: V1FinancialComponent;
  KosztSamochodZastepczy?: V1FinancialComponent;
  KosztSerwis?: V1FinancialComponent;
  KosztOpony?: V1FinancialComponent;
  KosztAdmin?: V1FinancialComponent;
  KosztRazemMarza?: V1FinancialComponent;
}

export interface V1DataOption {
  Numer: string;
  KalkulacjaId: number;
  OpcjeFabryczne: V1FactoryOption[];
  OpcjeSerwisowe: V1ServiceOption[];
  StawkaVat: number;

  // Dane kontraktu
  Marza: number;
  RodzajCzynszu: string;
  CzynszKwota: number;
  CzynszProcent: number;
  CzynszInicjalny: number;
  OkresUzytkowania: number;
  Przebieg: number;
  Rocznik: string;
  Marka: string;
  Model: { Id: number; Typ: string; DN: string };
  WersjaNadwozia: string;
  KategoriaSamar: string;
  MocSilnika: string;
  WersjaWyposazenia: string;
  RodzajPaliwa: string;
  HomologacjaSelected: string;
  KlasaWR: string;

  // Opony
  ZOponami: boolean;
  RozmiarOpon: {
    Szerokosc: string;
    Profil: string;
    Litera: string;
    Srednica: string;
  };
  KlasaOpon: string;
  LiczbaKompletowOponSelected: string;

  // Korekty
  InneKosztySerwisowania: number;
  PakietSerwisowy: number;
  PakietSerwisowyNazwa: string | null;
  KorektaRV: number;
  KalkulacjaWolumenowa: string | null;
  WiborProcent: number;
  MarzaFinansowaProcent: number;
  ProcentAmortyzacji?: number;
  Opis: string | null;
  Prywatna: boolean;

  // Kalkulacja samochodu
  CenaCennikowaNetto: number;
  CenaCennikowa: number;
  Metalik: boolean;
  TypRabatu: string;
  RabatProcent: number;
  RabatKwotaNetto: number;
  RabatKwota: number;

  // Opcje dodatkowe
  SamochodZastepczy: boolean;
  ExpressPlaciUbezpieczenie: boolean;
  CzyUwzgledniaSerwisowanie: boolean;
  CzyGPS: boolean;
  DoubezpieczenieKradziezy: boolean | null;
  NaukaJazdy: boolean | null;
  ZielonaKarta?: boolean;
  NNW?: boolean;
  ASS?: boolean;
  KosztUbezpieczeniaKorekta: number;
  KosztPrzygotowaniaDosprzedazyKorekta: number;
  KosztOponKorekta: number;

  // Wyniki
  GlownyMatrixParameters?: V1GlownyMatrixParameters;
}
