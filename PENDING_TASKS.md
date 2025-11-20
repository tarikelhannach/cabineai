# 📋 Tareas Pendientes para Producción

**Fecha:** 2025-11-20  
**Estado:** Después de correcciones de seguridad y bugs críticos

---

## ✅ **Completado en esta Sesión**

1. ✅ **Orden de middlewares corregido** - AuthMiddleware ejecuta antes de TenantMiddleware
2. ✅ **Logging de contraseñas eliminado** - No se loguean contraseñas en texto plano
3. ✅ **Redis password condicional** - Solo requiere password si está configurado
4. ✅ **Permisos de clerk restaurados** - Clerk tiene acceso completo a documentos (consistente con casos)
5. ✅ **Códigos HTTP estandarizados** - Uso de constantes `status.HTTP_*`
6. ✅ **Aislamiento multi-tenant** - Filtros por `firm_id` en todos los endpoints críticos
7. ✅ **TestSprite ejecutado** - 10 tests generados (fallaron por servidor mock, esperado)

---

## 🔴 **CRÍTICO - Antes de Producción**

### 1. **Implementar Envío de Contraseñas Temporales**
**Ubicación:** `backend/app/routes/auth.py` líneas 222, 240

**Problema:**
- Las contraseñas temporales se generan pero no se envían
- Hay un TODO para implementar email/SMS

**Acción Requerida:**
```python
# Crear servicio de notificaciones
backend/app/services/notification_service.py
- Implementar send_password_email()
- Integrar con servicio de email (SendGrid, AWS SES, etc.)
- O implementar SMS (Twilio, etc.)
```

**Prioridad:** 🔴 **ALTA** - Sin esto, los usuarios invitados no pueden acceder

---

### 2. **Re-ejecutar Tests con Servidor Real**
**Ubicación:** `testsprite_tests/`

**Problema:**
- Los tests de TestSprite fallaron porque se usó un servidor mock
- Necesitan ejecutarse contra el servidor backend real

**Acción Requerida:**
1. Iniciar servidor backend: `docker-compose up app1`
2. Re-ejecutar TestSprite: `mcp_TestSprite_testsprite_generate_code_and_execute`
3. Corregir endpoints que fallen

**Prioridad:** 🔴 **ALTA** - Validar que todo funciona correctamente

---

### 3. **Configurar Variables de Entorno para Producción**
**Ubicación:** `.env` o variables de entorno del servidor

**Variables Requeridas:**
```bash
# 🔒 CRÍTICAS (sin estas, la app no inicia en producción)
SECRET_KEY=<mínimo 32 caracteres aleatorios>
ALLOWED_ORIGINS=https://tu-dominio.com,https://www.tu-dominio.com

# 🔒 IMPORTANTES (para seguridad)
REDIS_PASSWORD=<password fuerte>
ELASTICSEARCH_PASSWORD=<password fuerte>
GRAFANA_ADMIN_PASSWORD=<password fuerte>
FLOWER_USER=<usuario>
FLOWER_PASSWORD=<password>

# 📧 OPCIONALES (para funcionalidad completa)
OPENAI_API_KEY=<para features AI>
STRIPE_SECRET_KEY=<para billing>
EMAIL_SERVICE_API_KEY=<para envío de contraseñas>
```

**Prioridad:** 🔴 **ALTA** - Sin estas, la app falla en producción

---

## 🟡 **IMPORTANTE - Próximas Semanas**

### 4. **Implementar Integración Email/SMS**
**Para:** Envío de contraseñas temporales y notificaciones

**Opciones:**
- **SendGrid** (recomendado para email)
- **AWS SES** (si usas AWS)
- **Twilio** (para SMS)
- **Resend** (moderno y simple)

**Prioridad:** 🟡 **MEDIA** - Bloquea funcionalidad de invitación de usuarios

---

### 5. **Validar Aislamiento Multi-Tenant**
**Ubicación:** Todos los endpoints de documentos, casos, usuarios

**Acción Requerida:**
- Crear tests específicos que validen que un usuario de Firm A no puede acceder a datos de Firm B
- Probar con diferentes roles (admin, lawyer, clerk, assistant)
- Validar que los filtros `firm_id` funcionan correctamente

**Prioridad:** 🟡 **MEDIA** - Crítico para seguridad multi-tenant

---

### 6. **Revisar y Corregir Tests Faltantes**
**Ubicación:** `testsprite_tests/testsprite-mcp-test-report.md`

**Tests que Fallaron (esperado con mock):**
- TC001: Login API
- TC002: Document Upload
- TC003: Case Creation
- TC004: Chat RAG
- TC005: AI Classification
- TC006: Document Drafting
- TC007: Search Documents
- TC008: User Creation
- TC009: Billing Checkout
- TC010: Audit Logs

**Acción Requerida:**
- Ejecutar tests con servidor real
- Corregir endpoints que fallen
- Agregar tests adicionales para casos edge

**Prioridad:** 🟡 **MEDIA** - Asegurar calidad del código

---

## 🟢 **MEJORAS - Próximos Meses**

### 7. **Optimizar Performance**
- Implementar cache invalidation strategy
- Optimizar queries de base de datos
- Implementar paginación eficiente
- Revisar índices de PostgreSQL

### 8. **Monitoreo y Logging**
- Configurar logging estructurado
- Integrar con sistema de monitoreo (Datadog, New Relic, etc.)
- Configurar alertas para errores críticos
- Dashboard de métricas

### 9. **Documentación**
- Documentar API con ejemplos
- Crear guía de deployment
- Documentar arquitectura
- Guía de troubleshooting

### 10. **Backup y Disaster Recovery**
- Configurar backups automáticos de PostgreSQL
- Plan de disaster recovery
- Documentar procedimientos de restauración

---

## 📊 **Resumen de Prioridades**

| Prioridad | Tarea | Estado | Estimación |
|-----------|-------|--------|------------|
| 🔴 Alta | Envío de contraseñas temporales | ❌ Pendiente | 2-4 horas |
| 🔴 Alta | Re-ejecutar tests con servidor real | ❌ Pendiente | 1-2 horas |
| 🔴 Alta | Configurar variables de entorno | ❌ Pendiente | 30 min |
| 🟡 Media | Integración Email/SMS | ❌ Pendiente | 4-8 horas |
| 🟡 Media | Validar aislamiento multi-tenant | ❌ Pendiente | 2-4 horas |
| 🟡 Media | Corregir tests fallidos | ❌ Pendiente | 4-8 horas |
| 🟢 Baja | Optimizaciones de performance | ❌ Pendiente | 1-2 semanas |
| 🟢 Baja | Monitoreo y logging | ❌ Pendiente | 1 semana |
| 🟢 Baja | Documentación | ❌ Pendiente | 1 semana |
| 🟢 Baja | Backup y DR | ❌ Pendiente | 3-5 días |

---

## 🚀 **Checklist Pre-Producción**

Antes de desplegar a producción, verificar:

- [ ] Todas las variables de entorno configuradas
- [ ] SECRET_KEY generado y seguro (mínimo 32 caracteres)
- [ ] ALLOWED_ORIGINS configurado (sin wildcards)
- [ ] Passwords de servicios configurados (Redis, Elasticsearch, etc.)
- [ ] Envío de emails implementado y probado
- [ ] Tests pasando (mínimo 80% de cobertura)
- [ ] Aislamiento multi-tenant validado
- [ ] Logging configurado
- [ ] Monitoreo configurado
- [ ] Backups configurados
- [ ] Documentación actualizada
- [ ] Plan de rollback documentado

---

**Última actualización:** 2025-11-20

