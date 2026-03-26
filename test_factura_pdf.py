import sys
import os
sys.path.append(os.path.dirname(__file__))

from factura import generar_factura_pdf
from datetime import datetime

prestamo_data = {
    "id": "test-loan-1234",
    "monto": 2500000,
    "tasa_interes": 2.8,
    "cantidad_cuotas": 3,
    "fecha_desembolso": datetime.now().strftime("%Y-%m-%d")
}

usuario_data = {
    "nombre_completo": "Ana Torres",
    "documento_identidad": "987654321",
    "email": "ana.torres@example.com",
    "telefono": "3001234567"
}

cuotas_data = [
    {"numero_cuota": 1, "monto_cuota": 903333.33, "fecha_vencimiento": "2023-11-25"},
    {"numero_cuota": 2, "monto_cuota": 903333.33, "fecha_vencimiento": "2023-12-25"},
    {"numero_cuota": 3, "monto_cuota": 903333.34, "fecha_vencimiento": "2024-01-25"}
]

try:
    url = generar_factura_pdf(prestamo_data, usuario_data, cuotas_data)
    print("PDF OK:", url)
except Exception as e:
    print("Error:", e)
    sys.exit(1)
