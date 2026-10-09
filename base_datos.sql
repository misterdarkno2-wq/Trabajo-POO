-- Base de datos del sistema de prestamos de equipos
CREATE DATABASE IF NOT EXISTS laboratorio
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE laboratorio;

CREATE TABLE IF NOT EXISTS equipos (
    codigo      VARCHAR(20)  PRIMARY KEY,
    nombre      VARCHAR(100) NOT NULL,
    tipo        VARCHAR(50)  NOT NULL,
    prestado_a  VARCHAR(100) NULL
);

CREATE TABLE IF NOT EXISTS prestamos (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    codigo           VARCHAR(20)  NOT NULL,
    persona          VARCHAR(100) NOT NULL,
    fecha_prestamo   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_devolucion DATETIME     NULL,
    FOREIGN KEY (codigo) REFERENCES equipos(codigo)
);

-- Equipos de ejemplo
INSERT IGNORE INTO equipos (codigo, nombre, tipo) VALUES
    ('NB-01', 'Notebook Lenovo', 'Notebook'),
    ('PR-01', 'Proyector Epson', 'Proyector'),
    ('AR-01', 'Kit Arduino Uno', 'Kit Arduino');
