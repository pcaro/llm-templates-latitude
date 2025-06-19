# LLM-Templates-Latitude Plugin Design Document

## Resumen

El plugin `llm-templates-latitude` integra [Latitude](https://latitude.so/) con [LLM](https://llm.datasette.io/) como un **template loader**, permitiendo usar prompts gestionados en Latitude como templates de LLM que pueden ejecutarse con cualquier modelo.

## Funcionalidades Principales

### 1. Template Loader para Latitude

**Descripción**: Cargar prompts almacenados en Latitude como templates de LLM, que luego pueden usarse con cualquier modelo.

**Interfaz CLI**:
```bash
# Usar prompt de Latitude con cualquier modelo
llm -t lat:my-project/email-generator -m gpt-4 "Necesito cancelar nuestra reunión"

# Con parámetros del template
llm -t lat:marketing/email-template -m claude-3 \
  -p recipient "Juan" -p tone "formal" \
  "Producto nuevo lanzamiento"

# Solo prompt path (proyecto por defecto)
llm -t lat:welcome-email -m gpt-4 "Usuario nuevo registrado"
```

### 2. Integración Completa con LLM

**Descripción**: Los templates de Latitude funcionan como cualquier template nativo de LLM.

**Funcionalidades**:
```bash
# Streaming (funciona automáticamente)
llm -t lat:story-generator -m gpt-4 "Érase una vez..." --stream

# Guardar localmente para uso offline
llm -t lat:my-project/summarizer --save my-summarizer
llm -t my-summarizer -m claude-3 "Contenido a resumir"

# Conversaciones
llm -t lat:assistant -m gpt-4 "Hola" -c
llm -c "Continúa la conversación"
```

### 3. Gestión de Conversaciones

**Descripción**: Mantener contexto entre múltiples interacciones.

**Interfaz**:
```bash
# Iniciar conversación
llm -m latitude:assistant "Hola, necesito ayuda con Python" -c

# Continuar conversación
llm -c "¿Cómo manejo excepciones?"

# Listar conversaciones
llm logs -m latitude
```

### 4. Configuración de API Key

**Descripción**: Múltiples formas de configurar credenciales.

**Opciones**:
```bash
# Variable de entorno
export LATITUDE_API_KEY="lat_..."

# LLM keys
llm keys set latitude

# Por comando
llm -m latitude:prompt -o api_key "lat_..." "input"

# Archivo .env
LATITUDE_API_KEY=lat_...
```

### 5. Comandos Adicionales

**Listar prompts disponibles**:
```bash
llm latitude list-prompts
```

**Ver detalles de un prompt**:
```bash
llm latitude describe marketing/email-template
```

**Renderizar prompt localmente** (sin ejecutar):
```bash
llm latitude render email-template --parameters '{"name": "Juan"}'
```

### 6. Integración con Herramientas de Latitude

**Soporte para prompts con tools/functions**:
```python
# El plugin detectará automáticamente si un prompt usa herramientas
# y las manejará apropiadamente
llm -m latitude:data-analyzer "Analiza ventas Q4 2023"
```

### 7. Logging y Evaluaciones

**Crear logs en Latitude**:
```bash
# Log automático de todas las ejecuciones
llm -m latitude:prompt "input" --log

# Con metadata adicional
llm -m latitude:prompt "input" \
  --log-metadata '{"user_id": "123", "session": "abc"}'
```

**Trigger de evaluaciones**:
```bash
# Ejecutar evaluaciones después de la respuesta
llm -m latitude:prompt "input" --evaluate
```

## Arquitectura Técnica

### Componentes Principales

1. **LatitudeModel**: Clase principal que extiende `llm.Model`
   - Maneja la ejecución de prompts
   - Gestiona streaming y respuestas síncronas
   - Integra con el sistema de conversaciones de LLM

2. **LatitudeCommands**: Comandos CLI adicionales
   - `list-prompts`: Lista prompts disponibles
   - `describe`: Muestra detalles de un prompt
   - `render`: Renderiza un prompt localmente

3. **LatitudeEmbeddings** (futuro): Soporte para embeddings
   - Usar modelos de embedding de Latitude
   - Integración con sistema de embeddings de LLM

### Flujo de Ejecución

1. Usuario ejecuta comando LLM con modelo `latitude`
2. Plugin parsea el prompt path del model_id o de opciones
3. Autentica con Latitude usando API key
4. Ejecuta el prompt con parámetros proporcionados
5. Maneja respuesta (streaming o completa)
6. Opcionalmente crea logs y ejecuta evaluaciones

### Manejo de Errores

- Validación de API key antes de ejecutar
- Mensajes claros para errores de Latitude
- Fallback a opciones por defecto cuando sea apropiado
- Logging de errores para debugging

## Consideraciones de Implementación

### Dependencias
- `llm>=0.13`: Framework base
- `latitude-sdk>=0.4.0`: SDK oficial de Latitude
- `pydantic>=2.0`: Validación de opciones
- `python-dotenv`: Cargar variables de entorno

### Compatibilidad
- Python 3.9+
- Soporte para async/await
- Compatible con todas las funciones de LLM

### Testing
- Tests unitarios para cada componente
- Tests de integración con mocks de Latitude
- Tests E2E opcionales con cuenta de prueba

## Roadmap Futuro

1. **v0.1.0** (actual): Funcionalidad básica
   - Ejecución de prompts
   - Streaming
   - Configuración de API key

2. **v0.2.0**: Comandos avanzados
   - Listar y describir prompts
   - Renderizado local
   - Mejor manejo de errores

3. **v0.3.0**: Integración completa
   - Soporte para herramientas
   - Logging automático
   - Evaluaciones

4. **v0.4.0**: Características enterprise
   - Caché de prompts
   - Batch processing
   - Métricas y observabilidad
