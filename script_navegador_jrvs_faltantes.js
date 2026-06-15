// ========================================
// SCRIPT PARA EXTRAER JRVs FALTANTES - CON DATOS DEL ESQUELETO
// ========================================
// Ejecuta este script en la consola de tu navegador (F12 > Console)
// mientras estás en https://resultadosgenerales2025.cne.hn
//
// IMPORTANTE: Primero carga las 2 variables necesarias:
// 1. JRVS_FALTANTES: Array de números de JRV faltantes [123, 456, 789, ...]
// 2. ESQUELETO_JRVS: JSON con la estructura completa de todas las JRVs
//
// El script buscará cada JRV faltante en el esqueleto para obtener
// sus datos jerárquicos (departamento/municipio/zona/puesto)

const BASE_URL = "https://resultadosgenerales2025-api.cne.hn";

// Verificar que existe JRVS_FALTANTES
if (typeof JRVS_FALTANTES === 'undefined') {
    console.error('❌ Error: No se encontró JRVS_FALTANTES');
    console.error('💡 Primero carga el array de JRVs faltantes');
    throw new Error('JRVS_FALTANTES no definido');
}

// Verificar que existe ESQUELETO_JRVS
if (typeof ESQUELETO_JRVS === 'undefined') {
    console.error('❌ Error: No se encontró ESQUELETO_JRVS');
    console.error('💡 Primero carga el JSON del esqueleto completo');
    throw new Error('ESQUELETO_JRVS no definido');
}

console.log(`✅ ${JRVS_FALTANTES.length.toLocaleString()} JRVs faltantes cargadas`);
console.log(`✅ ${ESQUELETO_JRVS.length.toLocaleString()} JRVs en el esqueleto`);

// Crear un Map para búsqueda rápida de JRVs en el esqueleto
console.log('🔍 Creando índice de JRVs del esqueleto...');
const esqueletoMap = new Map();
for (const jrv of ESQUELETO_JRVS) {
    esqueletoMap.set(jrv.numero_jrv, jrv);
}
console.log(`✅ Índice creado con ${esqueletoMap.size.toLocaleString()} JRVs`);

// Variable global para almacenar resultados
window.resultadosFaltantes = [];

// Estadísticas de progreso
let progreso = {
    total: JRVS_FALTANTES.length,
    procesadas: 0,
    exitosas: 0,
    errores: 0,
    inicio: new Date()
};

// ============================================================================
// FUNCIÓN PARA ESPERAR ENTRE PETICIONES
// ============================================================================

const esperar = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// ============================================================================
// FUNCIÓN PARA OBTENER DATOS DE UNA JRV ESPECÍFICA
// ============================================================================

async function obtenerDatosJRV(jrvData) {
    const url = `${BASE_URL}/esc/v1/presentacion-resultados`;

    const payload = {
        "codigos": [],
        "tipco": "01",  // Tipo de consulta: Presidencial
        "depto": jrvData.id_departamento,
        "comuna": "00",
        "mcpio": jrvData.id_municipio,
        "zona": jrvData.id_zona,
        "pesto": jrvData.id_puesto,
        "mesa": jrvData.numero_jrv
    };

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        return { success: true, data };

    } catch (error) {
        console.error(`❌ Error JRV ${jrvData.numero_jrv}:`, error.message);
        return { success: false, error: error.message };
    }
}

// ============================================================================
// FUNCIÓN PARA OBTENER ACTAS VÁLIDAS DE UNA JRV
// ============================================================================

async function obtenerActasValidas(jrvData) {
    const url = `${BASE_URL}/esc/v1/presentacion-resultados/actas-validas`;

    const payload = {
        "codigos": [],
        "tipco": "01",
        "depto": jrvData.id_departamento,
        "comuna": "00",
        "mcpio": jrvData.id_municipio,
        "zona": jrvData.id_zona,
        "pesto": jrvData.id_puesto,
        "mesa": jrvData.numero_jrv
    };

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            return null;
        }

        return await response.json();

    } catch (error) {
        return null;
    }
}

// ============================================================================
// FUNCIÓN PARA OBTENER VOTOS EN BLANCO DE UNA JRV
// ============================================================================

async function obtenerVotosBlanco(jrvData) {
    const url = `${BASE_URL}/esc/v1/presentacion-resultados/votos`;

    const payload = {
        "codigos": ["996"],  // Código 996 = Votos en blanco
        "tipco": "01",
        "depto": jrvData.id_departamento,
        "comuna": "00",
        "mcpio": jrvData.id_municipio,
        "zona": jrvData.id_zona,
        "pesto": jrvData.id_puesto,
        "mesa": jrvData.numero_jrv
    };

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            return 0;
        }

        const data = await response.json();
        return typeof data === 'number' ? data : 0;

    } catch (error) {
        return 0;
    }
}

// ============================================================================
// FUNCIÓN PARA OBTENER VOTOS NULOS DE UNA JRV
// ============================================================================

async function obtenerVotosNulos(jrvData) {
    const url = `${BASE_URL}/esc/v1/presentacion-resultados/votos`;

    const payload = {
        "codigos": ["997", "998"],  // Códigos 997 y 998 = Votos nulos
        "tipco": "01",
        "depto": jrvData.id_departamento,
        "comuna": "00",
        "mcpio": jrvData.id_municipio,
        "zona": jrvData.id_zona,
        "pesto": jrvData.id_puesto,
        "mesa": jrvData.numero_jrv
    };

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            return 0;
        }

        const data = await response.json();
        return typeof data === 'number' ? data : 0;

    } catch (error) {
        return 0;
    }
}

// ============================================================================
// FUNCIÓN PARA PROCESAR UNA JRV COMPLETA
// ============================================================================

async function procesarJRV(numeroJRV) {
    progreso.procesadas++;

    // Buscar datos de la JRV en el esqueleto
    const jrvData = esqueletoMap.get(numeroJRV);

    if (!jrvData) {
        console.warn(`⚠️  JRV ${numeroJRV} no encontrada en el esqueleto, se omitirá`);
        progreso.errores++;
        return null;
    }

    // Obtener datos de votos, actas, votos blancos y nulos en paralelo
    const [resultadoVotos, actasValidas, votosBlanco, votosNulos] = await Promise.all([
        obtenerDatosJRV(jrvData),
        obtenerActasValidas(jrvData),
        obtenerVotosBlanco(jrvData),
        obtenerVotosNulos(jrvData)
    ]);

    if (!resultadoVotos.success) {
        progreso.errores++;
        return null;
    }

    const data = resultadoVotos.data;

    // Extraer información básica (incluye datos jerárquicos del esqueleto)
    const acta = {
        // Datos jerárquicos del esqueleto
        id_departamento: jrvData.id_departamento,
        departamento: jrvData.departamento,
        id_municipio: jrvData.id_municipio,
        municipio: jrvData.municipio,
        id_zona: jrvData.id_zona,
        zona: jrvData.zona,
        id_puesto: jrvData.id_puesto,
        puesto: jrvData.puesto,

        // Datos de la JRV
        numero_jrv: numeroJRV,
        fecha_corte: data.fecha_corte || null,

        // Votos por partido
        votos_dc: 0,
        votos_libre: 0,
        votos_pinu: 0,
        votos_liberal: 0,
        votos_nacional: 0,
        votos_nulos: votosNulos,  // Usar valor obtenido de la petición
        votos_blanco: votosBlanco,  // Usar valor obtenido de la petición

        // Estadísticas de actas
        cantidad_total_actas: actasValidas?.total || 0,
        verificado: actasValidas?.verificacion || 0,
        cantidad_inconsistencias: actasValidas?.inconsistencias || 0,
        publicado: actasValidas?.publicadas || 0,
        en_espera: actasValidas?.espera || 0,
        correctas: actasValidas?.correctas || 0,
        inconsistencias: actasValidas?.inconsistencias || 0
    };

    // Extraer votos de candidatos
    if (data.candidatos && Array.isArray(data.candidatos)) {
        for (const candidato of data.candidatos) {
            const parpoId = candidato.parpo_id;
            const votos = candidato.votos || 0;

            switch (parpoId) {
                case "0001":
                    acta.votos_dc = votos;
                    break;
                case "0002":
                    acta.votos_libre = votos;
                    break;
                case "0003":
                    acta.votos_pinu = votos;
                    break;
                case "0004":
                    acta.votos_liberal = votos;
                    break;
                case "0005":
                    acta.votos_nacional = votos;
                    break;
            }
        }
    }

    // Extraer votos nulos y en blanco
    if (data.votosNulos !== undefined) {
        acta.votos_nulos = data.votosNulos;
    }
    if (data.votosBlanco !== undefined) {
        acta.votos_blanco = data.votosBlanco;
    }

    // Calcular error de suma
    const sumaVotos = acta.votos_dc + acta.votos_libre + acta.votos_pinu +
                     acta.votos_liberal + acta.votos_nacional +
                     acta.votos_nulos + acta.votos_blanco;

    acta.error_suma = (data.gran_total && sumaVotos !== data.gran_total) ? 1 : 0;

    // Etiquetas
    acta.etiquetas = data.etiquetas || "";

    // URL del acta PDF (si existe)
    if (data.url_acta_pdf) {
        acta.url_acta_pdf = data.url_acta_pdf;
    }

    progreso.exitosas++;
    return acta;
}

// ============================================================================
// FUNCIÓN PRINCIPAL - EXTRAER TODAS LAS JRVs FALTANTES
// ============================================================================

async function extraerJRVsFaltantes() {
    console.log("\n" + "=".repeat(80));
    console.log("🚀 INICIANDO EXTRACCIÓN DE JRVs FALTANTES");
    console.log("=".repeat(80));
    console.log(`📊 Total a procesar: ${JRVS_FALTANTES.length.toLocaleString()} JRVs`);
    console.log(`⏱️  Tiempo estimado: ${Math.ceil(JRVS_FALTANTES.length * 0.15 / 60)} minutos (aprox)`);
    console.log("=".repeat(80) + "\n");

    progreso.inicio = new Date();
    window.resultadosFaltantes = [];

    for (let i = 0; i < JRVS_FALTANTES.length; i++) {
        const numeroJRV = JRVS_FALTANTES[i];

        // Procesar JRV
        const resultado = await procesarJRV(numeroJRV);

        if (resultado) {
            window.resultadosFaltantes.push(resultado);
        }

        // Mostrar progreso cada 50 JRVs
        if ((i + 1) % 50 === 0 || i === JRVS_FALTANTES.length - 1) {
            mostrarProgreso();
        }

        // Esperar entre peticiones (0.1 segundos)
        await esperar(400);
    }

    // Resumen final
    mostrarResumenFinal();
}

// ============================================================================
// FUNCIÓN PARA MOSTRAR PROGRESO
// ============================================================================

function mostrarProgreso() {
    const porcentaje = (progreso.procesadas / progreso.total * 100).toFixed(2);
    const ahora = new Date();
    const tiempoTranscurrido = (ahora - progreso.inicio) / 1000; // segundos
    const velocidad = progreso.procesadas / tiempoTranscurrido; // JRVs por segundo
    const tiempoRestante = (progreso.total - progreso.procesadas) / velocidad; // segundos

    console.log(
        `📊 Progreso: ${progreso.procesadas}/${progreso.total} (${porcentaje}%) | ` +
        `✅ ${progreso.exitosas} | ❌ ${progreso.errores} | ` +
        `⏱️  ~${Math.ceil(tiempoRestante / 60)} min restantes`
    );
}

// ============================================================================
// FUNCIÓN PARA MOSTRAR RESUMEN FINAL
// ============================================================================

function mostrarResumenFinal() {
    const ahora = new Date();
    const tiempoTotal = ((ahora - progreso.inicio) / 1000 / 60).toFixed(2); // minutos

    console.log("\n" + "=".repeat(80));
    console.log("✅ EXTRACCIÓN COMPLETADA");
    console.log("=".repeat(80));
    console.log(`📊 Total procesadas: ${progreso.procesadas.toLocaleString()}`);
    console.log(`✅ Exitosas: ${progreso.exitosas.toLocaleString()}`);
    console.log(`❌ Errores: ${progreso.errores.toLocaleString()}`);
    console.log(`⏱️  Tiempo total: ${tiempoTotal} minutos`);
    console.log("=".repeat(80));
    console.log(`\n💾 Resultados guardados en: window.resultadosFaltantes`);
    console.log(`📦 Total registros: ${window.resultadosFaltantes.length.toLocaleString()}\n`);
    console.log("💡 Para descargar el JSON, ejecuta:");
    console.log("   descargarJSON(window.resultadosFaltantes, 'resultados_jrvs_faltantes.json')");
    console.log("=".repeat(80) + "\n");
}

// ============================================================================
// FUNCIÓN PARA DESCARGAR RESULTADOS COMO JSON
// ============================================================================

function descargarJSON(datos, nombreArchivo = 'resultados_jrvs_faltantes.json') {
    const jsonStr = JSON.stringify(datos, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = nombreArchivo;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    console.log(`✅ Archivo ${nombreArchivo} descargado`);
}

// ============================================================================
// FUNCIÓN PARA VER PROGRESO EN CUALQUIER MOMENTO
// ============================================================================

function verProgreso() {
    mostrarProgreso();
    console.log(`\n💾 Resultados parciales: ${window.resultadosFaltantes.length.toLocaleString()} actas guardadas`);
}

// ============================================================================
// FUNCIÓN DE PRUEBA - EXTRAER SOLO UNA JRV PARA VALIDAR
// ============================================================================

async function extraerUnSoloJRVFaltante(numeroJRV) {
    console.log("\n" + "=".repeat(80));
    console.log("🧪 EXTRACCIÓN DE PRUEBA - UNA SOLA JRV");
    console.log("=".repeat(80));

    // Si no se proporciona número, usar la primera del array
    if (!numeroJRV) {
        if (JRVS_FALTANTES.length === 0) {
            console.error("❌ No hay JRVs faltantes para probar");
            console.log("💡 Proporciona un número de JRV: extraerUnSoloJRVFaltante(123)");
            return;
        }
        numeroJRV = JRVS_FALTANTES[0];
        console.log(`\n🎯 Usando primera JRV faltante: ${numeroJRV}`);
    } else {
        console.log(`\n🎯 Probando con JRV: ${numeroJRV}`);
    }

    // Buscar en el esqueleto
    const jrvData = esqueletoMap.get(numeroJRV);

    if (!jrvData) {
        console.error(`❌ JRV ${numeroJRV} NO encontrada en el esqueleto`);
        console.log("\n💡 Verifica que ESQUELETO_JRVS contenga esta JRV");
        return;
    }

    console.log("\n✅ Datos del esqueleto encontrados:");
    console.log(`   Departamento: ${jrvData.departamento} (${jrvData.id_departamento})`);
    console.log(`   Municipio: ${jrvData.municipio} (${jrvData.id_municipio})`);
    console.log(`   Zona: ${jrvData.zona} (${jrvData.id_zona})`);
    console.log(`   Puesto: ${jrvData.puesto.substring(0, 60)}... (${jrvData.id_puesto})`);
    console.log(`   Número JRV: ${jrvData.numero_jrv}`);

    console.log("\n🔄 Haciendo peticiones a la API...");

    // Resetear progreso
    progreso.inicio = new Date();
    progreso.procesadas = 0;
    progreso.exitosas = 0;
    progreso.errores = 0;

    // Procesar la JRV
    const resultado = await procesarJRV(numeroJRV);

    if (!resultado) {
        console.error("\n❌ Error al procesar la JRV");
        console.log("💡 Revisa los errores anteriores");
        return;
    }

    console.log("\n✅ JRV procesada exitosamente!");
    console.log("\n" + "=".repeat(80));
    console.log("📊 RESULTADO OBTENIDO:");
    console.log("=".repeat(80));
    console.log(JSON.stringify(resultado, null, 2));
    console.log("=".repeat(80));

    // Guardar en resultados
    window.resultadosFaltantes = [resultado];

    console.log("\n💾 Resultado guardado en: window.resultadosFaltantes[0]");
    console.log("\n💡 Para ver solo los votos:");
    console.log("   console.log({");
    console.log("     DC: window.resultadosFaltantes[0].votos_dc,");
    console.log("     LIBRE: window.resultadosFaltantes[0].votos_libre,");
    console.log("     PINU: window.resultadosFaltantes[0].votos_pinu,");
    console.log("     Liberal: window.resultadosFaltantes[0].votos_liberal,");
    console.log("     Nacional: window.resultadosFaltantes[0].votos_nacional,");
    console.log("     Nulos: window.resultadosFaltantes[0].votos_nulos,");
    console.log("     Blanco: window.resultadosFaltantes[0].votos_blanco");
    console.log("   });");

    console.log("\n✅ Si todo se ve correcto, ejecuta:");
    console.log("   await extraerJRVsFaltantes()");
    console.log("=".repeat(80) + "\n");
}

// ============================================================================
// INSTRUCCIONES DE USO
// ============================================================================

console.log("\n" + "=".repeat(80));
console.log("📋 INSTRUCCIONES DE USO");
console.log("=".repeat(80));
console.log("");
console.log("📌 VARIABLES REQUERIDAS (ya cargadas):");
console.log(`   ✅ JRVS_FALTANTES: ${JRVS_FALTANTES.length.toLocaleString()} JRVs`);
console.log(`   ✅ ESQUELETO_JRVS: ${ESQUELETO_JRVS.length.toLocaleString()} JRVs`);
console.log("");
console.log("🧪 PRIMERO - Probar con una sola JRV:");
console.log("   await extraerUnSoloJRVFaltante(928)        // Con número específico");
console.log("   await extraerUnSoloJRVFaltante()           // Sin parámetro usa la primera");
console.log("");
console.log("1️⃣  Para iniciar extracción completa:");
console.log("   await extraerJRVsFaltantes()");
console.log("");
console.log("2️⃣  Para ver progreso durante la extracción:");
console.log("   verProgreso()");
console.log("");
console.log("3️⃣  Para descargar resultados:");
console.log("   descargarJSON(window.resultadosFaltantes, 'resultados_jrvs_faltantes.json')");
console.log("");
console.log("💡 El script buscará cada JRV faltante en el esqueleto y usará");
console.log("   sus datos jerárquicos (depto/municipio/zona/puesto) para las peticiones");
console.log("=".repeat(80) + "\n");
