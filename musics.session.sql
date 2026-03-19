CREATE DATABASE IF NOT EXISTS musichistory;
USE musichistory;

-- Crear tabla de Usuarios
CREATE TABLE Usuarios (
    telefono VARCHAR(15) PRIMARY KEY,
    nombre VARCHAR(100),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crear tabla de Historial
CREATE TABLE Historial (
    id_mensaje INT AUTO_INCREMENT PRIMARY KEY,
    telefono_usuario VARCHAR(35),
    rol ENUM('user', 'assistant') NOT NULL,
    contenido TEXT NOT NULL,
    fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (telefono_usuario) REFERENCES Usuarios(telefono) ON DELETE CASCADE
);
