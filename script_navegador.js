// ========================================
// SCRIPT PARA EXTRAER DATOS DEL CNE
// ========================================
// Ejecuta este script en la consola de tu navegador (F12 > Console)
// mientras estás en https://resultadosgenerales2025.cne.hn

const DEPARTAMENTOS = [
    { id_departamento: "01", departamento: "ATLANTIDA" },
    { id_departamento: "06", departamento: "CHOLUTECA" },
    { id_departamento: "02", departamento: "COLON" },
    { id_departamento: "03", departamento: "COMAYAGUA" },
    { id_departamento: "04", departamento: "COPAN" },
    { id_departamento: "05", departamento: "CORTES" },
    { id_departamento: "07", departamento: "EL PARAISO" },
    { id_departamento: "08", departamento: "FRANCISCO MORAZAN" },
    { id_departamento: "09", departamento: "GRACIAS A DIOS" },
    { id_departamento: "10", departamento: "INTIBUCA" },
    { id_departamento: "11", departamento: "ISLAS DE LA BAHIA" },
    { id_departamento: "12", departamento: "LA PAZ" },
    { id_departamento: "13", departamento: "LEMPIRA" },
    { id_departamento: "14", departamento: "OCOTEPEQUE" },
    { id_departamento: "15", departamento: "OLANCHO" },
    { id_departamento: "16", departamento: "SANTA BARBARA" },
    { id_departamento: "17", departamento: "VALLE" },
    { id_departamento: "20", departamento: "VOTO EN EL EXTERIOR" },
    { id_departamento: "18", departamento: "YORO" }
];

const BASE_URL = "https://resultadosgenerales2025-api.cne.hn";

// Función para esperar entre peticiones
const esperar = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// Función para obtener municipios de un departamento
async function obtenerMunicipios(idDepartamento) {
    const url = `${BASE_URL}/esc/v1/actas-documentos/01/${idDepartamento}/municipios`;
    try {
        const response = await fetch(url);
        return await response.json();
    } catch (error) {
        console.error(`Error obteniendo municipios de ${idDepartamento}:`, error);
        return [];
    }
}

// Función para obtener votos de un municipio
async function obtenerVotos(idDepartamento, idMunicipio) {
    const url = `${BASE_URL}/esc/v1/presentacion-resultados`;
    const payload = {
        codigos: [],
        tipco: "01",
        depto: idDepartamento,
        comuna: "00",
        mcpio: idMunicipio,
        zona: "",
        pesto: "",
        mesa: 0
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
        return await response.json();
    } catch (error) {
        console.error(`Error obteniendo votos de ${idDepartamento}-${idMunicipio}:`, error);
        return null;
    }
}

// Función para obtener actas válidas
async function obtenerActas(idDepartamento, idMunicipio) {
    const url = `${BASE_URL}/esc/v1/presentacion-resultados/actas-validas`;
    const payload = {
        codigos: [],
        tipco: "01",
        depto: idDepartamento,
        comuna: "00",
        mcpio: idMunicipio,
        zona: "",
        pesto: "",
        mesa: 0
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
        return await response.json();
    } catch (error) {
        console.error(`Error obteniendo actas de ${idDepartamento}-${idMunicipio}:`, error);
        return null;
    }
}

// Función principal
async function extraerTodosLosDatos() {
    console.log("🚀 Iniciando extracción de datos del CNE...");
    console.log(`📊 Total departamentos a procesar: ${DEPARTAMENTOS.length}`);

    const resultados = [];
    let totalMunicipios = 0;

    for (let i = 0; i < DEPARTAMENTOS.length; i++) {
        const depto = DEPARTAMENTOS[i];
        console.log(`\n📍 [${i + 1}/${DEPARTAMENTOS.length}] Procesando: ${depto.departamento}`);

        // Obtener municipios del departamento
        const municipios = await obtenerMunicipios(depto.id_departamento);
        console.log(`   ✅ ${municipios.length} municipios encontrados`);

        for (let j = 0; j < municipios.length; j++) {
            const muni = municipios[j];
            console.log(`   🏘️  [${j + 1}/${municipios.length}] ${muni.municipio}`);

            // Obtener votos y actas
            const [votos, actas] = await Promise.all([
                obtenerVotos(depto.id_departamento, muni.id_municipio),
                obtenerActas(depto.id_departamento, muni.id_municipio)
            ]);

            // Extraer solo Partido Nacional y Liberal
            let votosNacional = 0;
            let votosLiberal = 0;

            if (votos && votos.candidatos) {
                const nacional = votos.candidatos.find(c => c.parpo_id === "0005");
                const liberal = votos.candidatos.find(c => c.parpo_id === "0004");
                votosNacional = nacional ? nacional.votos : 0;
                votosLiberal = liberal ? liberal.votos : 0;
            }

            const resultado = {
                id_departamento: depto.id_departamento,
                departamento: depto.departamento,
                id_municipio: muni.id_municipio,
                municipio: muni.municipio,
                fecha_corte: votos?.fecha_corte || "",
                votos_nacional: votosNacional,
                votos_liberal: votosLiberal,
                total_actas: actas?.total || 0,
                actas_publicadas: actas?.publicadas || 0,
                actas_correctas: actas?.correctas || 0
            };

            resultados.push(resultado);
            totalMunicipios++;

            // Esperar 500ms entre municipios para no saturar
            await esperar(500);
        }

        // Esperar 1 segundo entre departamentos
        await esperar(1000);
    }

    console.log(`\n✅ ¡Extracción completada!`);
    console.log(`📊 Total municipios procesados: ${totalMunicipios}`);
    console.log(`\n💾 Para descargar el JSON, ejecuta:`);
    console.log(`descargarJSON(resultados);`);

    // Guardar en variable global para poder descargarlo
    window.resultadosCNE = resultados;

    return resultados;
}

// Función para descargar el JSON
function descargarJSON(datos) {
    const dataStr = JSON.stringify(datos, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'resultados_municipios.json';
    link.click();
    URL.revokeObjectURL(url);
    console.log("✅ Archivo descargado: resultados_municipios.json");
}

// Función para ver progreso
function verProgreso() {
    if (window.resultadosCNE) {
        console.log(`📊 Municipios procesados hasta ahora: ${window.resultadosCNE.length}`);
        console.log(`📥 Para descargar: descargarJSON(window.resultadosCNE)`);
    } else {
        console.log("⚠️ Aún no hay datos. Ejecuta primero: extraerTodosLosDatos()");
    }
}

// ========================================
// INSTRUCCIONES DE USO
// ========================================
console.log(`
╔════════════════════════════════════════════════════════════╗
║          SCRIPT DE EXTRACCIÓN DE DATOS DEL CNE            ║
╚════════════════════════════════════════════════════════════╝

📋 INSTRUCCIONES:

1. Asegúrate de estar en: https://resultadosgenerales2025.cne.hn
2. Abre la consola del navegador (F12 > Console)
3. Copia y pega este script completo
4. Ejecuta el siguiente comando:

   await extraerTodosLosDatos()

5. Espera ~15-20 minutos (verás el progreso en la consola)
6. Cuando termine, descarga el JSON con:

   descargarJSON(window.resultadosCNE)

📊 COMANDOS DISPONIBLES:

- extraerTodosLosDatos()  : Inicia la extracción
- verProgreso()           : Ver cuántos municipios se han procesado
- descargarJSON(datos)    : Descargar el JSON

⚠️ IMPORTANTE:
- No cierres la pestaña del navegador durante el proceso
- No cambies de pestaña (puede pausar el script)
- Si se interrumpe, ejecuta: descargarJSON(window.resultadosCNE)
  para guardar lo que se haya procesado hasta el momento

🚀 ¡Listo! Ahora ejecuta: await extraerTodosLosDatos()
`);
