# PhillyData

Python recreation of the original PhillyData PowerShell app.

## Run

```bash
python phillydata.py
```

## Notes

- Default login is `admin` with a blank password (override with `PHILLYDATA_USERNAME` and `PHILLYDATA_PASSWORD`).
- The app provides dataset loading, search filtering, and map-link support for crime rows.
- Dataset-loading failures are handled in the UI with clear error messages.
