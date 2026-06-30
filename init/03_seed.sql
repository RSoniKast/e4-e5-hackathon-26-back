-- =====================================================================
-- Jeu de donnees minimal pour tester (a supprimer avant la prod).
-- =====================================================================

INSERT INTO site (nom, ville, code_postal) VALUES
    ('Campus Metz Technopole', 'Metz', '57070');

INSERT INTO batiment (site_id, nom) VALUES
    (1, 'Batiment A'),
    (1, 'Batiment B');

INSERT INTO salle (batiment_id, nom, capacite, heure_fermeture) VALUES
    (1, 'A101', 30, '19:00'),
    (1, 'A102', 24, '19:00'),
    (2, 'Labo Chimie', 16, '18:00');   -- salle "securite" (temp/humidite/CO2)

INSERT INTO calculateur (salle_id, nom, ip_adresse, mac_adresse) VALUES
    (1, 'Capteur A101', '192.168.10.11', '00:1B:44:11:3A:B7'),
    (3, 'Capteur Labo', '192.168.10.12', '00:1B:44:11:3A:C8');

-- Quelques releves pour la visualisation
INSERT INTO releve (calculateur_id, temperature, luminosite, presence, fenetre_ouverte, porte_ouverte) VALUES
    (1, 21.5, 640, false, false, false),
    (1, 22.0, 12,  false, true,  false),   -- fenetre ouverte le soir -> alerte potentielle
    (2, 23.1, 300, true,  false, false);

-- Admin de demo : REMPLACER le hash par un vrai hash genere cote app.
INSERT INTO app_user (username, password_hash, role) VALUES
    ('admin', '$REMPLACER_PAR_UN_HASH_BCRYPT', 'administrateur');
