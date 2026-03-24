# 💳 PrestaRápido System

Sistema web de solicitud y evaluación de créditos — Mínimo Producto Viable (MVP) desarrollado con **FastAPI**, **PostgreSQL** y **HTML/CSS/JS** vanilla.

---

## 📋 Tabla de Contenido

- [Requisitos previos](#-requisitos-previos)
- [Instalación](#-instalación)
- [Configuración](#-configuración)
- [Ejecución](#-ejecución)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Páginas disponibles](#-páginas-disponibles)
- [Endpoints de la API](#-endpoints-de-la-api)
- [Reglas de negocio](#-reglas-de-negocio)
- [Tecnologías utilizadas](#-tecnologías-utilizadas)

---

## ✅ Requisitos previos

Asegúrate de tener instalado lo siguiente antes de continuar:

| Herramienta | Versión recomendada | Descarga |
|---|---|---|
| Python | 3.11+ | [python.org](https://www.python.org/downloads/) |
| PostgreSQL | 14+ | [postgresql.org](https://www.postgresql.org/download/) |
| Git | Cualquiera | [git-scm.com](https://git-scm.com/) |

> ⚠️ **Windows:** Instala Python desde [python.org](https://www.python.org/downloads/) y **no** desde la Microsoft Store para evitar problemas con entornos virtuales.

---

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/D-valin/PrestaRapido-System.git
cd PrestaRapido-System/prestarapido
```

### 2. Crear y activar el entorno virtual

**Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
```

**Mac / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

> El prompt debe mostrar `(venv)` al inicio cuando esté activo.

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuración

### 1. Crear la base de datos en PostgreSQL

Abre **pgAdmin** o la terminal de PostgreSQL y ejecuta:

```sql
CREATE DATABASE prestarapidoz;
```

### 2. Crear el archivo `.env`

Crea un archivo llamado `.env` dentro de la carpeta `prestarapido/` con el siguiente contenido:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=prestarapidoz
DB_USER=postgres
DB_PASSWORD=tu_contraseña_aqui
SECRET_KEY=1gjh4f3gh24vhn2n4m5bm6h54jh64hjg4jgf
```

> 🔒 **Importante:** Nunca subas el archivo `.env` a GitHub. Agrega `.env` a tu `.gitignore`.

### 3. (Opcional) Crear las tablas manualmente

Las tablas se crean automáticamente al iniciar el servidor. Si prefieres crearlas manualmente:

```bash
psql -U postgres -d prestarapidoz -f schema.sql
```

---

## ▶️ Ejecución

Desde la carpeta `prestarapido/` con el entorno virtual activo:

```bash
python -m uvicorn main:app --reload
```

Si todo está correcto verás:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
✅ Tablas creadas y migradas correctamente.
```

Abre tu navegador en:

```
http://127.0.0.1:8000
```

Te redirigirá automáticamente al login.

---

## 📁 Estructura del proyecto

```
PrestaRapido-System/
└── prestarapido/
    ├── main.py            # Endpoints REST (CRUD usuarios, préstamos, cuotas, pagos)
    ├── auth.py            # Autenticación JWT (login, cambio y recuperación de contraseña)
    ├── models.py          # Modelos Pydantic de entrada/salida
    ├── evaluacion.py      # Motor de evaluación crediticia (RNF-01 a RNF-08)
    ├── db.py              # Conexión a PostgreSQL y migración de tablas
    ├── schema.sql         # Script DDL de la base de datos
    ├── requirements.txt   # Dependencias del proyecto
    ├── .env               # Variables de entorno (NO subir a GitHub)
    └── static/
        ├── style.css      # Estilos compartidos
        ├── login.html     # Inicio de sesión
        ├── registro.html  # Registro de usuario
        ├── dashboard.html # Panel principal
        ├── solicitar.html # Solicitud de crédito con evaluación automática
        ├── prestamos.html # Historial de préstamos
        ├── cuotas.html    # Detalle de cuotas por préstamo
        ├── pagos.html     # Historial de pagos por cuota
        ├── perfil.html    # Perfil y cambio de contraseña
        └── recuperar.html # Recuperación de contraseña
```

---

## 🌐 Páginas disponibles

| Página | URL | Descripción |
|---|---|---|
| Login | `/static/login.html` | Inicio de sesión |
| Registro | `/static/registro.html` | Crear cuenta nueva |
| Dashboard | `/static/dashboard.html` | Panel principal con estadísticas |
| Solicitar crédito | `/static/solicitar.html` | Formulario con evaluación automática |
| Mis préstamos | `/static/prestamos.html` | Historial con filtros por estado |
| Cuotas | `/static/cuotas.html?id={id}` | Cuotas de un préstamo |
| Pagos | `/static/pagos.html?cuota={id}` | Historial de pagos por cuota |
| Mi perfil | `/static/perfil.html` | Editar datos y cambiar contraseña |
| Recuperar contraseña | `/static/recuperar.html` | Flujo de recuperación en 3 pasos |
| Docs API | `/docs` | Documentación interactiva (Swagger) |

---

## 📡 Endpoints de la API

La documentación interactiva completa está disponible en **`http://127.0.0.1:8000/docs`** una vez que el servidor esté corriendo.

### Autenticación
| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/auth/login` | Iniciar sesión, retorna token JWT |
| `POST` | `/auth/cambiar-password` | Cambiar contraseña (requiere token) |
| `POST` | `/auth/recuperar-password` | Recuperar contraseña sin sesión |

### Usuarios
| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/usuarios/` | Registrar usuario |
| `GET` | `/usuarios/` | Listar usuarios |
| `GET` | `/usuarios/{id}` | Obtener usuario por ID |
| `PUT` | `/usuarios/{id}` | Actualizar usuario |
| `DELETE` | `/usuarios/{id}` | Eliminar usuario |

### Préstamos
| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/prestamos/evaluar` | Evaluar elegibilidad sin crear préstamo |
| `POST` | `/prestamos/` | Crear préstamo (con evaluación automática) |
| `GET` | `/prestamos/` | Listar préstamos |
| `GET` | `/prestamos/{id}` | Obtener préstamo por ID |
| `GET` | `/usuarios/{id}/prestamos` | Préstamos de un usuario |
| `PUT` | `/prestamos/{id}` | Actualizar préstamo |
| `DELETE` | `/prestamos/{id}` | Eliminar préstamo |

### Cuotas y Pagos
| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/cuotas/` | Crear cuota |
| `GET` | `/prestamos/{id}/cuotas` | Cuotas de un préstamo |
| `PUT` | `/cuotas/{id}` | Actualizar cuota |
| `POST` | `/pagos/` | Registrar pago |
| `GET` | `/cuotas/{id}/pagos` | Pagos de una cuota |

---

## 📐 Reglas de negocio

Al crear un préstamo, el sistema evalúa automáticamente las siguientes condiciones:

| Regla | Condición | Resultado si falla |
|---|---|---|
| **RNF-01** Elegibilidad | Edad entre 21 y 65 años, ingreso > $0 | Rechazo automático |
| **RNF-02** Historial | Score calculado por pagos anteriores en plataforma | Penaliza el score |
| **RNF-03** Score crediticio | Score ≥ 40/100 mínimo | Rechazo si score < 40 |
| **RNF-04** Ratio deuda/ingreso | Deuda mensual / ingreso | > 70% → rechazo; 40–70% → revisión |
| **RNF-05** Límite de monto | Bajo: $10M / Medio: $5M / Alto: $2M COP | Rechazo si supera el límite |
| **RNF-06** Plazo | Máximo 3 cuotas | Rechazo si supera 3 meses |
| **RNF-07** Tasa de interés | Asignada por el sistema según riesgo | Bajo: 1.5% / Medio: 2.8% / Alto: 4.2% |
| **RNF-08** Estado final | Todas las condiciones evaluadas | Aprobado / En revisión / Rechazado |

> El endpoint `POST /prestamos/evaluar` permite previsualizar el resultado sin guardar nada.

---

## 🛠️ Tecnologías utilizadas

- **[FastAPI](https://fastapi.tiangolo.com/)** — Framework backend con documentación automática
- **[PostgreSQL](https://www.postgresql.org/)** — Base de datos relacional
- **[psycopg2](https://www.psycopg.org/)** — Conector PostgreSQL para Python
- **[Pydantic v2](https://docs.pydantic.dev/)** — Validación de modelos de datos
- **[passlib + bcrypt](https://passlib.readthedocs.io/)** — Hashing de contraseñas
- **[python-jose](https://python-jose.readthedocs.io/)** — Tokens JWT
- **[python-dotenv](https://github.com/theskumar/python-dotenv)** — Variables de entorno
- **HTML / CSS / JavaScript** — Frontend sin frameworks

---

## 👤 Autor

**Juan Manuel Velez Arias** — Aprendiz SENA  
Proyecto desarrollado para el programa de formación CDMC — Ambiente 200
