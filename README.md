# Requisitos
+ Python 3.1*
+ PostgreSQL
+ Flask

# Configuracion

Primero crea tu .env con los siguientes valores:
```
DB_HOST=localhost
DB_USER=postgres
DB_PASSWORD=tu_contra
DB_NAME=facturacion_db
DB_PORT=tu_puerto

KEY_SECRET_ADMIN=coloca_una_clave_secreta
USER_ADMIN=admin
USER_PASSWORD=admin

FLASK_SECRET_KEY=coloca_aqui_una_clave_de_seguridad_para_flask
```

Crea tu entorno virtual `venv`
`python -m venv venv`

Accede a entorno con
Windows:`venv\Scripts\activate` o Linux:`source venv\bin\activate`

Instala las dependencias
`pip install -r requirements`

Crea una base de datos con nombre `facturacion_db`

Ejecuta el archivo `init_db.py`una unica vez para crear las tablas y procedimientos almacenados.

# Integrantes del proyecto
+ 2022100151 Arias Arias Fidel Reynaldo - Usuario: fidel-arias
+ 2022601021 Del Arroyo Calla Rafael Raul - Usuario: RafaelDelArroyoCalla
+ 2022404592 Laureano Tupac Yupanqui Natty Jimena - Usuario: natt25
+ 2022246652 Mamani Mendiguri Mirella Thiani - Usuario: MIRELLAMM4
+ 2020177181 Merma Alarcon Luis A. - Usuario: Wasausky16

# ENLACE DE GITHUB
`https://github.com/Fidel-Arias/ModuloFacturacion`

