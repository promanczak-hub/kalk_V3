-- Migration generated from V1 Express_test database extract

-- 1. LTRAdminUbezpieczenia (Stawki AC / OC w zaleznosci od roku i klasy)
DO $$
BEGIN
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (1, 0.0150, 1476.0000, NULL);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (2, 0.0150, 1476.0000, NULL);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (3, 0.0150, 1476.0000, NULL);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (4, 0.0150, 1476.0000, NULL);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (5, 0.0150, 1476.0000, NULL);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (5, 0.0150, 1750.0000, 9);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (4, 0.0150, 1750.0000, 9);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (3, 0.0150, 1750.0000, 9);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (2, 0.0150, 1750.0000, 9);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (1, 0.0150, 1750.0000, 9);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (6, 0.0150, 1750.0000, 9);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (6, 0.0150, 1476.0000, NULL);
END $$;

-- 2. LTRAdminWspolczynnikiSzkodowe (Wspolczynniki dla poszczegolnych klas)
DO $$
BEGIN
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (17, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (1, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (2, 1.0000, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (19, 1.1400, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (3, 1.0000, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (4, 1.0000, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (14, 1.9800, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 1.8200, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (5, 1.0000, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (6, 1.0800, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (21, 1.0000, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 1.0000, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (7, 1.3100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (13, 2.6200, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (8, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (12, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (20, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (9, 0.9300, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (24, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (23, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (22, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (10, 1.1300, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (11, 1.1200, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (18, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (16, 2.6200, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 1.0000, 1.0000);
END $$;

-- 3. LTRAdminParametry (Globalne nastawy szkodowosci i ryzyka ubezpieczeniowego)
UPDATE public.control_center SET
  ins_theft_doub_pct = 0.10,
  ins_driving_school_doub_pct = 0.5,
  ins_avg_damage_value = 2587,
  ins_avg_damage_mileage = 80000;
