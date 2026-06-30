-- =====================================================================
-- ClassroomObserv — Schema PostgreSQL
-- Couvre : sites, batiments, salles, calculateurs, personnels, classes,
--          eleves, liaisons N-N, releves de capteurs, journal d'etat, auth.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- pour chiffrement AES de colonnes sensibles (RGPD)

-- ---------------------------------------------------------------------
-- AUTH  (logigramme : "Verification des droits d'acces")
-- ---------------------------------------------------------------------
CREATE TABLE app_user (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,             -- hash (ex. bcrypt/argon2) cote app
    role          VARCHAR(20)  NOT NULL DEFAULT 'utilisateur'
                  CHECK (role IN ('utilisateur', 'administrateur')),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- HIERARCHIE  Site -> Batiment -> Salle
-- Regle : pas de batiment sans site, pas de salle sans batiment.
-- ---------------------------------------------------------------------
CREATE TABLE site (
    id          SERIAL PRIMARY KEY,
    nom         VARCHAR(150) NOT NULL,
    adresse     VARCHAR(255),
    ville       VARCHAR(100) NOT NULL,
    code_postal VARCHAR(10),
    latitude    DOUBLE PRECISION,                    -- geolocalisation optionnelle
    longitude   DOUBLE PRECISION,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- controle de doublons demande : nom + ville
    CONSTRAINT uq_site_nom_ville UNIQUE (nom, ville)
);

CREATE TABLE batiment (
    id         SERIAL PRIMARY KEY,
    -- RESTRICT = interdit de supprimer un site qui possede des batiments
    site_id    INTEGER NOT NULL REFERENCES site(id) ON DELETE RESTRICT,
    nom        VARCHAR(150) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_batiment_nom_site UNIQUE (site_id, nom)
);

CREATE TABLE salle (
    id              SERIAL PRIMARY KEY,
    batiment_id     INTEGER NOT NULL REFERENCES batiment(id) ON DELETE RESTRICT,
    nom             VARCHAR(150) NOT NULL,
    capacite        INTEGER CHECK (capacite >= 0),
    heure_fermeture TIME,                            -- pour l'alerte "salle ouverte apres une heure"
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- unicite du nom de salle dans un meme batiment
    CONSTRAINT uq_salle_nom_batiment UNIQUE (batiment_id, nom)
);

-- ---------------------------------------------------------------------
-- CALCULATEURS (capteurs / centrales) associes a une salle
-- ---------------------------------------------------------------------
CREATE TABLE calculateur (
    id          SERIAL PRIMARY KEY,
    -- SET NULL : un calculateur peut exister sans salle (en attente d'affectation)
    salle_id    INTEGER REFERENCES salle(id) ON DELETE SET NULL,
    nom         VARCHAR(150) NOT NULL,
    ip_adresse  INET   UNIQUE,                       -- type natif Postgres
    mac_adresse MACADDR UNIQUE,                       -- type natif Postgres
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- PERSONNELS
-- ---------------------------------------------------------------------
CREATE TABLE personnel (
    id          SERIAL PRIMARY KEY,
    identifiant VARCHAR(50)  NOT NULL UNIQUE,        -- unicite des identifiants utilisateurs
    nom         VARCHAR(100) NOT NULL,
    prenom      VARCHAR(100) NOT NULL,
    email       VARCHAR(255) UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- CLASSES
-- ---------------------------------------------------------------------
CREATE TABLE classe (
    id                      SERIAL PRIMARY KEY,
    nom                     VARCHAR(100) NOT NULL,
    niveau                  VARCHAR(50),
    annee_scolaire          VARCHAR(9)  NOT NULL,    -- ex. "2025-2026"
    professeur_principal_id INTEGER REFERENCES personnel(id) ON DELETE SET NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_classe_nom_annee UNIQUE (nom, annee_scolaire)
);

-- ---------------------------------------------------------------------
-- ELEVES
-- ---------------------------------------------------------------------
CREATE TABLE eleve (
    id          SERIAL PRIMARY KEY,
    identifiant VARCHAR(50)  NOT NULL UNIQUE,        -- controle d'unicite sur l'identifiant
    nom         VARCHAR(100) NOT NULL,
    prenom      VARCHAR(100) NOT NULL,
    email       VARCHAR(255),
    telephone   VARCHAR(30),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- LIAISONS N-N
-- ---------------------------------------------------------------------
CREATE TABLE personnel_salle (
    personnel_id INTEGER NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    salle_id     INTEGER NOT NULL REFERENCES salle(id)     ON DELETE CASCADE,
    PRIMARY KEY (personnel_id, salle_id)
);

CREATE TABLE personnel_classe (
    personnel_id INTEGER NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    classe_id    INTEGER NOT NULL REFERENCES classe(id)    ON DELETE CASCADE,
    matiere      VARCHAR(100) NOT NULL DEFAULT '',
    PRIMARY KEY (personnel_id, classe_id, matiere)
);

CREATE TABLE personnel_horaire (
    id           SERIAL PRIMARY KEY,
    personnel_id INTEGER NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    jour         SMALLINT NOT NULL CHECK (jour BETWEEN 1 AND 7),  -- 1=lundi
    heure_debut  TIME NOT NULL,
    heure_fin    TIME NOT NULL,
    CHECK (heure_fin > heure_debut)
);

-- Affectation eleve <-> classe.
-- Regle du sujet : "un eleve par classe et par annee".
-- annee_scolaire dupliquee ici volontairement pour rendre la contrainte simple a poser.
CREATE TABLE classe_eleve (
    classe_id      INTEGER NOT NULL REFERENCES classe(id) ON DELETE CASCADE,
    eleve_id       INTEGER NOT NULL REFERENCES eleve(id)  ON DELETE CASCADE,
    annee_scolaire VARCHAR(9) NOT NULL,
    PRIMARY KEY (classe_id, eleve_id),
    -- un eleve ne peut etre que dans UNE classe pour une annee donnee
    CONSTRAINT uq_eleve_annee UNIQUE (eleve_id, annee_scolaire)
);

-- ---------------------------------------------------------------------
-- RELEVES CAPTEURS (le "Collecteur IoT/API" ecrit ici ; la visualisation lit ici)
-- Snapshot complet par calculateur (cf. plages des specs capteurs du sujet).
-- ---------------------------------------------------------------------
CREATE TABLE releve (
    id              BIGSERIAL PRIMARY KEY,
    calculateur_id  INTEGER NOT NULL REFERENCES calculateur(id) ON DELETE CASCADE,
    temperature     NUMERIC(4,1) CHECK (temperature BETWEEN -20 AND 50),  -- °C
    luminosite      SMALLINT     CHECK (luminosite BETWEEN 0 AND 1023),   -- 10 bits
    presence        BOOLEAN,                                              -- HIGH/LOW
    fenetre_ouverte BOOLEAN,                                              -- contact fenetre
    porte_ouverte   BOOLEAN,
    mesure_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Index cle pour "derniere mesure d'une salle/calculateur" (visualisation rapide)
CREATE INDEX idx_releve_calc_time ON releve (calculateur_id, mesure_at DESC);

-- ---------------------------------------------------------------------
-- JOURNAL D'ETAT RESEAU (monitoring ping : journaliser les changements)
-- ---------------------------------------------------------------------
CREATE TABLE etat_calculateur_log (
    id             BIGSERIAL PRIMARY KEY,
    calculateur_id INTEGER NOT NULL REFERENCES calculateur(id) ON DELETE CASCADE,
    en_ligne       BOOLEAN NOT NULL,                -- true = vert, false = rouge
    change_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_etat_calc_time ON etat_calculateur_log (calculateur_id, change_at DESC);
