import os
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos

def generar_factura_pdf(prestamo, usuario, cuotas) -> str:
    """
    Genera un archivo PDF con los detalles del préstamo (factura) 
    y lo guarda en la carpeta static/facturas/.
    Retorna la URL relativa del archivo.
    """
    # Crear directorio si no existe
    facturas_dir = os.path.join(os.path.dirname(__file__), "static", "facturas")
    os.makedirs(facturas_dir, exist_ok=True)
    
    file_name = f"factura_{prestamo['id']}.pdf"
    file_path = os.path.join(facturas_dir, file_name)
    
    pdf = FPDF()
    pdf.add_page()
    
    # Fuentes y Título
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "PrestaRápido - Comprobante de Préstamo", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(5)
    
    # Información del Cliente
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Información del Cliente", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 6, f"Nombre: {usuario['nombre_completo']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Documento de Identidad: {usuario['documento_identidad']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Email: {usuario['email']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Teléfono: {usuario['telefono']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)
    
    # Detalles del Préstamo
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Detalles del Préstamo", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 6, f"ID de Préstamo: {prestamo['id']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Monto Aprobado: ${float(prestamo['monto']):,.2f}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Tasa de Interés: {float(prestamo['tasa_interes'])}% mensual", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Cantidad de Cuotas: {prestamo['cantidad_cuotas']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    try:
        if type(prestamo['fecha_desembolso']) is str:
            fecha_desc = datetime.strptime(prestamo['fecha_desembolso'], "%Y-%m-%d").strftime("%d-%m-%Y")
        else:
            fecha_desc = prestamo['fecha_desembolso'].strftime("%d-%m-%Y") if prestamo.get('fecha_desembolso') else datetime.now().strftime("%d-%m-%Y")
    except Exception:
        fecha_desc = str(prestamo.get('fecha_desembolso', ''))
    
    pdf.cell(0, 6, f"Fecha de Desembolso: {fecha_desc}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Calcular interés aplicado total
    interes_total = float(prestamo['monto']) * (float(prestamo['tasa_interes']) / 100) * int(prestamo['cantidad_cuotas'])
    total_a_pagar = float(prestamo['monto']) + interes_total
    
    pdf.cell(0, 6, f"Interés Total Aplicado: ${interes_total:,.2f}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Total a Pagar: ${total_a_pagar:,.2f}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)
    
    # Tabla de Amortización
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Cronograma de Pagos", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Encabezado de la tabla
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(40, 8, "No. Cuota", border=1, align="C")
    pdf.cell(60, 8, "Fecha Vencimiento", border=1, align="C")
    pdf.cell(50, 8, "Monto (con interés)", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    
    # Contenido de la tabla
    pdf.set_font("helvetica", "", 10)
    for cuota in cuotas:
        # Formatear fecha
        if type(cuota['fecha_vencimiento']) is str:
            venc = cuota['fecha_vencimiento']
        else:
            venc = cuota['fecha_vencimiento'].strftime("%d-%m-%Y")
        
        pdf.cell(40, 8, str(cuota['numero_cuota']), border=1, align="C")
        pdf.cell(60, 8, venc, border=1, align="C")
        pdf.cell(50, 8, f"${float(cuota['monto_cuota']):,.2f}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        
    pdf.ln(10)
    pdf.set_font("helvetica", "I", 9)
    pdf.cell(0, 5, "Este documento es un comprobante generado automáticamente.", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.cell(0, 5, "Agradecemos su preferencia por PrestaRápido.", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    
    pdf.output(file_path)
    
    return f"/static/facturas/{file_name}"
