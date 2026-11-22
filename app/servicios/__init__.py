"""Servicios: reglas de negocio y transacciones. Una clase por módulo.

Reciben la conexión y crean sus repositorios. Cada método público que escribe
es UNA transacción. No conocen HTTP ni JSON (ARQUITECTURA.md, sección 3).
"""
