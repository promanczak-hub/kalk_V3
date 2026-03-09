ALTER TABLE public.ltr_admin_korekta_wr_markas
    ADD CONSTRAINT ltr_admin_korekta_wr_markas_samar_class_fk
    FOREIGN KEY (samar_class_id) REFERENCES public.samar_classes(id) ON DELETE CASCADE;

ALTER TABLE public.ltr_admin_korekta_wr_markas
    ADD CONSTRAINT ltr_admin_korekta_wr_markas_unique_class_fuel_brand
    UNIQUE (samar_class_id, rodzaj_paliwa, brand_name);

ALTER TABLE public.ltr_admin_wspolczynniki_szkodowe
    ADD CONSTRAINT ltr_admin_wspolczynniki_szkodowe_samar_class_fk
    FOREIGN KEY (samar_class_id) REFERENCES public.samar_classes(id) ON DELETE CASCADE;

ALTER TABLE public.ltr_admin_ubezpieczenia
    ADD CONSTRAINT ltr_admin_ubezpieczenia_samar_class_fk
    FOREIGN KEY (samar_class_id) REFERENCES public.samar_classes(id) ON DELETE CASCADE;
