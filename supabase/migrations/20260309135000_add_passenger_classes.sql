-- Migration: Add 28 passenger SAMAR classes with specific IDs
-- These IDs (100+) are required by subsequent migrations like options_rv
INSERT INTO samar_classes (id, name, category, size_class, example_models)
VALUES
  (100, 'Podstawowa - A MINI', 'Podstawowa', 'A', 'Fiat 500, Hyundai i10, Kia Picanto, Toyota Aygo X, Dacia Spring'),
  (101, 'Podstawowa - B MAŁE', 'Podstawowa', 'B', 'Volkswagen Polo, Renault Clio, Toyota Yaris, Skoda Fabia, Opel Corsa'),
  (102, 'Podstawowa - C NIŻSZA ŚREDNIA', 'Podstawowa', 'C', 'Volkswagen Golf, Toyota Corolla, Skoda Octavia, Kia Ceed, Ford Focus'),
  (103, 'Podstawowa - D ŚREDNIA', 'Podstawowa', 'D', 'BMW Serii 3, Audi A5, Tesla Model 3, Toyota Camry, Volkswagen Passat'),
  (104, 'Podstawowa - E WYŻSZA', 'Podstawowa', 'E', 'BMW Serii 5, Audi A6, Mercedes Klasa E, Volvo S90, Lexus ES'),
  (105, 'Podstawowa - F LUKSUSOWE', 'Podstawowa', 'F', 'BMW Serii 7, Audi A8, Mercedes Klasa S, Porsche Panamera, Lexus LS'),
  (106, 'Podstawowa - G SUPER LUKSUSOWE', 'Podstawowa', 'G', 'Bentley Flying Spur, Rolls-Royce Ghost, Rolls-Royce Phantom'),
  (107, 'Vany - B MICROVANY', 'Vany', 'B', 'Honda Jazz'),
  (108, 'Vany - C MINIVANY', 'Vany', 'C', 'BMW 2 Active Tourer, Dacia Jogger, Mercedes Klasa B, Volkswagen Touran'),
  (109, 'Vany - D VANY', 'Vany', 'D', 'Forthing U-Tour'),
  (110, 'Vany - E WYŻSZA', 'Vany', 'E', 'Forthing V-Tour, Voyah Dream'),
  (111, 'Vany - F LUKSUSOWE', 'Vany', 'F', 'Lexus LM'),
  (112, 'Sportowo-rekreacyjne - A MINI', 'Sportowo-rekreacyjne', 'A', 'Fiat 500 Cabrio, Abarth 500 Cabrio'),
  (113, 'Sportowo-rekreacyjne - B MAŁE', 'Sportowo-rekreacyjne', 'B', 'Mini Cabrio'),
  (114, 'Sportowo-rekreacyjne - C NIŻSZA ŚREDNIA', 'Sportowo-rekreacyjne', 'C', 'BMW Serii 4, Ford Mustang, Porsche 718'),
  (115, 'Sportowo-rekreacyjne - D ŚREDNIA', 'Sportowo-rekreacyjne', 'D', 'Mercedes CLE'),
  (116, 'Sportowo-rekreacyjne - E WYŻSZA', 'Sportowo-rekreacyjne', 'E', 'Alpine A110, BMW Z4, Mazda MX-5'),
  (117, 'Sportowo-rekreacyjne - F LUKSUSOWE', 'Sportowo-rekreacyjne', 'F', 'BMW Serii 8, Porsche 911, Mercedes SL'),
  (118, 'Sportowo-rekreacyjne - G SUPER LUKSUSOWE', 'Sportowo-rekreacyjne', 'G', 'Ferrari 296, Lamborghini Revuelto, Aston Martin DB12'),
  (119, 'Terenowo-rekreacyjne (SUV) - B MAŁE', 'Terenowo-rekreacyjne (SUV)', 'B', 'Ford Puma, Toyota Yaris Cross, Volkswagen T-Cross, Hyundai Kona'),
  (120, 'Terenowo-rekreacyjne (SUV) - C NIŻSZA ŚREDNIA', 'Terenowo-rekreacyjne (SUV)', 'C', 'BMW X3, Audi Q5, Hyundai Santa Fe, Kia Sorento'),
  (121, 'Terenowo-rekreacyjne (SUV) - D ŚREDNIA', 'Terenowo-rekreacyjne (SUV)', 'D', 'BMW X1, Audi Q3, Hyundai Tucson, Kia Sportage'),
  (122, 'Terenowo-rekreacyjne (SUV) - E WYŻSZA', 'Terenowo-rekreacyjne (SUV)', 'E', 'BMW X7, Mercedes GLS, Lotus Eletre'),
  (123, 'Terenowo-rekreacyjne (SUV) - F LUKSUSOWE', 'Terenowo-rekreacyjne (SUV)', 'F', 'Lamborghini Urus, Bentley Bentayga, Rolls-Royce Cullinan'),
  (124, 'Terenowo-rekreacyjne (SUV) - G SUPER LUKSUSOWE', 'Terenowo-rekreacyjne (SUV)', 'G', 'BMW X5, Porsche Cayenne, Mercedes GLE'),
  (125, 'Kombivany - H KOMBI-VANY', 'Kombivany', 'H', 'Citroen Berlingo, Peugeot Rifter, Volkswagen Caddy'),
  (126, 'Minibusy - I MINIBUSY', 'Minibusy', 'I', 'Volkswagen Multivan, Mercedes V-Class, Hyundai Staria'),
  (127, 'Kempingowe - K KEMPINGOWE', 'Kempingowe', 'K', 'Volkswagen California, Mercedes Marco Polo')
ON CONFLICT (name) DO UPDATE SET
  category = EXCLUDED.category,
  size_class = EXCLUDED.size_class,
  example_models = EXCLUDED.example_models;
