-- ==========================================================
-- SCRIPT DE CRÉATION DE LA BASE DE DONNÉES
-- ==========================================================

-- Création de la base de données (si elle n'existe pas)
CREATE DATABASE IF NOT EXISTS patrimoine_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE patrimoine_db;

-- ----------------------------------------------------------
-- Table `utilisateurs`
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `utilisateurs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL,
    `email` VARCHAR(120) NOT NULL UNIQUE,
    `password` VARCHAR(255) NOT NULL,
    `city` VARCHAR(100),
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ----------------------------------------------------------
-- Table `patrimoines`
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `patrimoines` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(200) NOT NULL,
    `description` TEXT NOT NULL,
    `category` VARCHAR(50) NOT NULL,
    `latitude` DOUBLE NOT NULL,
    `longitude` DOUBLE NOT NULL,
    `city` VARCHAR(100),
    `user_id` INT NOT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_user` FOREIGN KEY (`user_id`) REFERENCES `utilisateurs`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------
-- INSERTIONS DE TEST
-- ----------------------------------------------------------

-- Insertion d'utilisateurs (Mot de passe en clair pour le test: 'password123')
INSERT INTO `utilisateurs` (`name`, `email`, `password`, `city`) VALUES
('Jean', 'jean@example.com', 'password123', 'Paris'),
('Marie', 'marie@example.com', 'password123', 'Lomé'),
('Admin', 'admin@test.com', 'password123', 'Abidjan');

-- Insertion de patrimoines (liés aux IDs des utilisateurs ci-dessus)
-- On suppose que Jean Dupont a l'ID 1 et Marie l'ID 2
INSERT INTO `patrimoines` (`name`, `description`, `category`, `latitude`, `longitude`, `city`, `user_id`) VALUES
('Tour Eiffel', 'Monument emblématique de Paris, construit pour l\'Exposition universelle de 1889.', 'monument', 48.8584, 2.2945, 'Paris', 1),
('Grand Marché de Lomé', 'Cœur économique et culturel de la capitale togolaise.', 'site', 6.1256, 1.2254, 'Lomé', 2),
('Musée du Louvre', 'L\'un des plus grands musées d\'art et d\'histoire au monde.', 'musee', 48.8606, 2.3376, 'Paris', 1),
('Parc National de Fazao-Malfakassa', 'Le plus grand parc national du Togo.', 'parc', 9.2500, 1.1167, 'Kara', 2);

