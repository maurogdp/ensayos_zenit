# ZipGrade CSV Downloader

## Pasos rápidos
1. Crea y activa un entorno virtual (opcional pero recomendado).
2. `pip install -r requirements.txt`
3. Crea un archivo `.env` junto al script con:
```
ZIPGRADE_EMAIL="tu_correo@dominio.com"
ZIPGRADE_PASSWORD="tu_password"
DOWNLOAD_DIR="/ruta/descargas/opcional"
```
4. Corre el script:
```
python zipgrade_scraper.py --headful
```
5. Opciones útiles:
- `--only "Parcial 1"` filtra por título
- `--dry-run` no descarga, solo lista
- `--max 10` limita la cantidad
