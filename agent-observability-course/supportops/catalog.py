"""Datos ficticios de SupportOps: clientes, pedidos y base de conocimiento. Todo sintético y determinista."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from .clock import SIM_EPOCH_S, stable_rng

DB_SEED = 7
N_CUSTOMERS = 200
N_ORDERS = 600

FIRST = ["Lucía", "Mateo", "Sofía", "Hugo", "Valeria", "Diego", "Carmen", "Pablo", "Elena", "Andrés", "Marta", "Iván"]
LAST = ["García", "Martínez", "López", "Sánchez", "Pérez", "Gómez", "Ruiz", "Díaz", "Torres", "Navarro"]
PRODUCTS = [  # (sku, nombre, precio EUR)
    ("SKU-1001", "Teclado mecánico K87", 89.90), ("SKU-1002", "Ratón inalámbrico M3", 39.90),
    ("SKU-1003", "Monitor 27'' QHD", 289.00), ("SKU-1004", "SSD NVMe 1 TB", 79.90),
    ("SKU-1005", "Tarjeta gráfica RTX-X 12 GB", 549.00), ("SKU-1006", "Router Wi-Fi 7", 159.00),
    ("SKU-1007", "Webcam 4K", 99.00), ("SKU-1008", "Auriculares ANC H5", 129.00),
    ("SKU-1009", "Fuente 750 W 80+ Gold", 119.00), ("SKU-1010", "Portátil Ultra 14", 1099.00),
]
CARRIERS = ["DHL", "SEUR", "Correos Express"]


@dataclass(frozen=True)
class KBDoc:
    doc_id: str
    title: str
    text: str


KB_DOCS: list[KBDoc] = [
    KBDoc("KB-001", "Política de devoluciones",
          "Puedes devolver cualquier producto en un plazo de 30 días naturales desde la entrega si está sin usar y en su "
          "embalaje original. El reembolso se emite al método de pago original en un máximo de 5 días laborables tras "
          "recibir el producto en nuestro almacén."),
    KBDoc("KB-002", "Garantía legal",
          "Todos los productos tienen 3 años de garantía legal. Si un producto falla por defecto de fabricación, se "
          "repara o se sustituye sin coste. La garantía no cubre golpes, líquidos ni uso indebido."),
    KBDoc("KB-003", "Plazos y costes de envío",
          "El envío estándar tarda de 2 a 4 días laborables y es gratuito en pedidos superiores a 50 euros. El envío "
          "urgente (24 horas) cuesta 9,90 euros. Los pedidos realizados antes de las 14:00 salen el mismo día."),
    KBDoc("KB-004", "Seguimiento de pedidos",
          "Recibirás un correo con el número de seguimiento cuando el pedido salga del almacén. Puedes consultar el "
          "estado en tu cuenta o escribirnos con el número de pedido, con formato ORD-00000."),
    KBDoc("KB-005", "Cancelar un pedido",
          "Un pedido en estado procesando puede cancelarse sin coste. Si ya ha sido enviado, debes rechazar la entrega o "
          "solicitar una devolución cuando lo recibas."),
    KBDoc("KB-006", "Instalar drivers de la tarjeta gráfica",
          "Desinstala el driver anterior con el modo seguro, descarga la última versión desde la web del fabricante y "
          "reinicia. Si la pantalla parpadea, revisa que el cable de alimentación PCIe esté bien conectado."),
    KBDoc("KB-007", "Configurar el router Wi-Fi 7",
          "Conecta el router al módem por el puerto WAN, accede a 192.168.0.1 y sigue el asistente. Para mejor "
          "rendimiento usa la banda de 6 GHz con dispositivos compatibles con Wi-Fi 7 y el canal automático."),
    KBDoc("KB-008", "Actualizar el firmware del teclado mecánico",
          "Descarga la utilidad de firmware, conecta el teclado por cable y pulsa Actualizar. No lo desconectes durante "
          "el proceso, que dura unos dos minutos. Se conservan tus macros."),
    KBDoc("KB-009", "Métodos de pago y facturas",
          "Aceptamos tarjeta, transferencia y pago a plazos. Las facturas se generan automáticamente y puedes "
          "descargarlas en tu cuenta en formato PDF. Nunca te pediremos por chat el número completo de tu tarjeta."),
    KBDoc("KB-010", "Cambio de dirección de entrega",
          "Puedes cambiar la dirección mientras el pedido esté en estado procesando. Una vez enviado, contacta con el "
          "transportista usando el número de seguimiento."),
    KBDoc("KB-011", "Productos defectuosos o dañados en el transporte",
          "Si recibes un producto dañado, haz fotos del embalaje y del producto y abre una incidencia en 48 horas. "
          "Enviaremos un recambio sin coste o reembolsaremos el importe completo."),
    KBDoc("KB-012", "Soporte prioritario para clientes premium",
          "Los clientes premium tienen soporte prioritario con respuesta humana en menos de 2 horas y recogida gratuita "
          "de devoluciones a domicilio."),
    KBDoc("KB-013", "Compatibilidad de la fuente de alimentación",
          "La fuente de 750 W 80+ Gold es compatible con tarjetas gráficas de hasta 450 W de consumo y dispone de dos "
          "conectores PCIe de 8 pines y un conector 12VHPWR."),
    KBDoc("KB-014", "Privacidad y datos personales",
          "Tratamos tus datos únicamente para gestionar pedidos y soporte. Puedes solicitar acceso, rectificación o "
          "eliminación escribiendo a privacidad en nuestro sitio web."),
]


@lru_cache(maxsize=1)
def customers() -> dict[str, dict[str, Any]]:
    rng = stable_rng("customers", DB_SEED)
    out: dict[str, dict[str, Any]] = {}
    for i in range(1, N_CUSTOMERS + 1):
        cid = f"C-{i:04d}"
        first, last = rng.choice(FIRST), rng.choice(LAST)
        out[cid] = {
            "customer_id": cid,
            "name": f"{first} {last}",
            "email": f"{first.lower().replace('á','a').replace('í','i').replace('é','e')}.{last.lower().replace('á','a').replace('í','i').replace('é','e').replace('ó','o')}{i}@example.com",
            "phone": f"+34 6{rng.randint(10,99)} {rng.randint(100,999)} {rng.randint(100,999)}",
            "tier": "premium" if rng.random() < 0.2 else "standard",
            "card_number": f"4000 0000 {rng.randint(1000,9999)} {rng.randint(1000,9999)}",  # PAN ficticio
        }
    return out


@lru_cache(maxsize=1)
def orders() -> dict[str, dict[str, Any]]:
    rng = stable_rng("orders", DB_SEED)
    out: dict[str, dict[str, Any]] = {}
    for i in range(1, N_ORDERS + 1):
        oid = f"ORD-{i:05d}"
        cid = f"C-{rng.randint(1, N_CUSTOMERS):04d}"
        sku, name, price = rng.choice(PRODUCTS)
        status = rng.choices(["processing", "shipped", "delivered", "cancelled"], weights=[10, 20, 60, 10])[0]
        age_days = rng.randint(0, 60)  # antigüedad del pedido respecto al origen del tiempo simulado
        placed = SIM_EPOCH_S - age_days * 86400
        delivered_days_ago = None
        if status == "delivered":
            delivered_days_ago = rng.randint(0, max(0, age_days - 2)) if age_days > 2 else 0
        out[oid] = {
            "order_id": oid, "customer_id": cid, "status": status,
            "items": [{"sku": sku, "name": name, "qty": 1, "price_eur": price}],
            "total_eur": price, "carrier": rng.choice(CARRIERS) if status in ("shipped", "delivered") else None,
            "tracking": f"TRK{rng.randint(10**8, 10**9 - 1)}" if status in ("shipped", "delivered") else None,
            "eta_days": rng.randint(1, 4) if status in ("processing", "shipped") else None,
            "placed_at": placed,
            "delivered_days_ago": delivered_days_ago,
        }
    return out


@lru_cache(maxsize=1)
def stock() -> dict[str, int]:
    rng = stable_rng("stock", DB_SEED)
    return {sku: rng.randint(0, 40) for sku, _, _ in PRODUCTS}
