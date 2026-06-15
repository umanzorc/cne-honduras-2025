// ========================================
// SCRIPT DETALLADO COMPLETO PARA EXTRAER DATOS DEL CNE POR JRV
// Incluye TODOS los partidos, votos nulos y votos en blanco
// ========================================
// Ejecuta este script en la consola de tu navegador (F12 > Console)
// mientras estás en https://resultadosgenerales2025.cne.hn
//
// IMPORTANTE: Antes de ejecutar este script, carga el archivo de exclusiones:
// 1. Ejecuta primero: generar_exclusiones.py (en Python)
// 2. Luego en el navegador, carga jrvs_a_excluir.js (pega el contenido aquí)
// 3. Finalmente ejecuta este script
//
// Si no tienes exclusiones, define un Set vacío:
// const JRVS_A_EXCLUIR = new Set();

// Verificar si existe JRVS_A_EXCLUIR, si no, crear vacío
if (typeof JRVS_A_EXCLUIR === 'undefined') {
    console.warn('⚠️  No se encontró JRVS_A_EXCLUIR. Se procesarán TODAS las JRVs.');
    console.warn('💡 Para optimizar, ejecuta primero generar_exclusiones.py y carga jrvs_a_excluir.js');
    var JRVS_A_EXCLUIR = new Set();
} else {
    console.log(`✅ Cargadas ${JRVS_A_EXCLUIR.size} JRVs a excluir`);
}

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
        console.error(`❌ Error obteniendo municipios de ${idDepartamento}:`, error);
        return [];
    }
}

// Función para obtener zonas de un municipio
async function obtenerZonas(idDepartamento, idMunicipio) {
    const url = `${BASE_URL}/esc/v1/actas-documentos/01/${idDepartamento}/${idMunicipio}/00/zonas`;
    try {
        const response = await fetch(url);
        return await response.json();
    } catch (error) {
        console.error(`❌ Error obteniendo zonas de ${idDepartamento}-${idMunicipio}:`, error);
        return [];
    }
}

// Función para obtener centros de votación (puestos) de una zona
async function obtenerPuestos(idDepartamento, idMunicipio, idZona) {
    const url = `${BASE_URL}/esc/v1/actas-documentos/01/${idDepartamento}/${idMunicipio}/${idZona}/puestos`;
    try {
        const response = await fetch(url);
        return await response.json();
    } catch (error) {
        console.error(`❌ Error obteniendo puestos de ${idDepartamento}-${idMunicipio}-${idZona}:`, error);
        return [];
    }
}

// Función para obtener mesas (JRVs) de un centro de votación
async function obtenerMesas(idDepartamento, idMunicipio, idZona, idPuesto) {
    const url = `${BASE_URL}/esc/v1/actas-documentos/01/${idDepartamento}/${idMunicipio}/${idZona}/${idPuesto}/mesas`;
    try {
        const response = await fetch(url);
        return await response.json();
    } catch (error) {
        console.error(`❌ Error obteniendo mesas de ${idDepartamento}-${idMunicipio}-${idZona}-${idPuesto}:`, error);
        return [];
    }
}

// Función para obtener votos de una JRV específica
async function obtenerVotosJRV(idDepartamento, idMunicipio, idZona, idPuesto, numeroMesa) {
    const url = `${BASE_URL}/esc/v1/presentacion-resultados`;
    const payload = {
        codigos: [],
        tipco: "01",
        // depto: "03",
        // // comuna: "00",
        // mcpio: "008",
        // zona: "02",
        // pesto: "004",
        mesa: 2165
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
        console.error(`❌ Error obteniendo votos de mesa ${numeroMesa}:`, error);
        return null;
    }
}

// Función para obtener actas válidas de una JRV específica
async function obtenerActasJRV(idDepartamento, idMunicipio, idZona, idPuesto, numeroMesa) {
    const url = `${BASE_URL}/esc/v1/presentacion-resultados/actas-validas`;
    const payload = {
        codigos: [],
        tipco: "01",
        depto: idDepartamento,
        comuna: "00",
        mcpio: idMunicipio,
        zona: idZona,
        pesto: idPuesto,
        mesa: numeroMesa
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
        console.error(`❌ Error obteniendo actas de mesa ${numeroMesa}:`, error);
        return null;
    }
}

// Función para obtener votos en blanco de una JRV específica
async function obtenerVotosBlanco(idDepartamento, idMunicipio, idZona, idPuesto, numeroMesa) {
    const url = `${BASE_URL}/esc/v1/presentacion-resultados/votos`;
    const payload = {
        codigos: ["996"],  // Código 996 = Votos en blanco
        tipco: "01",
        depto: idDepartamento,
        comuna: "00",
        mcpio: idMunicipio,
        zona: idZona,
        pesto: idPuesto,
        mesa: numeroMesa
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
        const resultado = await response.json();
        return typeof resultado === 'number' ? resultado : 0;
    } catch (error) {
        console.error(`❌ Error obteniendo votos en blanco de mesa ${numeroMesa}:`, error);
        return 0;
    }
}

// Función para obtener votos nulos de una JRV específica
async function obtenerVotosNulos(idDepartamento, idMunicipio, idZona, idPuesto, numeroMesa) {
    const url = `${BASE_URL}/esc/v1/presentacion-resultados/votos`;
    const payload = {
        codigos: ["997", "998"],  // Códigos 997 y 998 = Votos nulos
        tipco: "01",
        depto: idDepartamento,
        comuna: "00",
        mcpio: idMunicipio,
        zona: idZona,
        pesto: idPuesto,
        mesa: numeroMesa
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
        const resultado = await response.json();
        return typeof resultado === 'number' ? resultado : 0;
    } catch (error) {
        console.error(`❌ Error obteniendo votos nulos de mesa ${numeroMesa}:`, error);
        return 0;
    }
}

// Función principal
async function extraerTodosLosDatosDetallados() {
    console.log("🚀 Iniciando extracción DETALLADA de datos del CNE (por JRV)...");
    console.log(`📊 Total departamentos a procesar: ${DEPARTAMENTOS.length}`);
    console.log(`⚠️ ADVERTENCIA: Este proceso puede tardar VARIAS HORAS debido a la cantidad de JRVs`);
    console.log(`💡 TIP: No cierres esta pestaña y déjala activa\n`);

    const resultados = [];
    let totalJRVs = 0;
    let errorCount = 0;

    for (let i = 0; i < DEPARTAMENTOS.length; i++) {
        const depto = DEPARTAMENTOS[i];
        console.log(`\n${"=".repeat(80)}`);
        console.log(`📍 [${i + 1}/${DEPARTAMENTOS.length}] DEPARTAMENTO: ${depto.departamento} (${depto.id_departamento})`);
        console.log(`${"=".repeat(80)}`);

        // Obtener municipios del departamento
        const municipios = await obtenerMunicipios(depto.id_departamento);
        console.log(`   ✅ ${municipios.length} municipios encontrados`);
        await esperar(500);

        for (let j = 0; j < municipios.length; j++) {
            const muni = municipios[j];
            console.log(`\n   🏘️  [${j + 1}/${municipios.length}] MUNICIPIO: ${muni.municipio} (${muni.id_municipio})`);

            // Obtener zonas del municipio
            const zonas = await obtenerZonas(depto.id_departamento, muni.id_municipio);
            console.log(`      📍 ${zonas.length} zona(s) encontrada(s): ${zonas.map(z => z.zona).join(', ')}`);
            await esperar(300);

            for (let k = 0; k < zonas.length; k++) {
                const zona = zonas[k];
                console.log(`\n      🌍 [${k + 1}/${zonas.length}] ZONA: ${zona.zona} (${zona.id_zona})`);

                // Obtener centros de votación (puestos) de la zona
                const puestos = await obtenerPuestos(depto.id_departamento, muni.id_municipio, zona.id_zona);
                console.log(`         🏢 ${puestos.length} centro(s) de votación encontrado(s)`);
                await esperar(300);

                for (let l = 0; l < puestos.length; l++) {
                    const puesto = puestos[l];
                    console.log(`\n         📦 [${l + 1}/${puestos.length}] CENTRO: ${puesto.puesto.substring(0, 50)}${puesto.puesto.length > 50 ? '...' : ''}`);

                    // Obtener mesas (JRVs) del centro de votación
                    const mesas = await obtenerMesas(depto.id_departamento, muni.id_municipio, zona.id_zona, puesto.id_puesto);
                    console.log(`            🗳️  ${mesas.length} JRV(s) encontrada(s)`);
                    await esperar(200);

                    for (let m = 0; m < mesas.length; m++) {
                        const mesa = mesas[m];

                        // Verificar si esta JRV ya está en Drive (excluir)
                        if (JRVS_A_EXCLUIR.has(String(mesa.numero))) {
                            console.log(`            ✅ JRV ${mesa.numero}: Ya tiene URL en Drive, omitiendo...`);
                            continue;
                        }

                        // Solo procesar mesas publicadas
                        if (mesa.publicada === 0) {
                            console.log(`            ⏭️  JRV ${mesa.numero}: Sin publicar, omitiendo...`);
                            continue;
                        }

                        console.log(`            ⚙️  [${m + 1}/${mesas.length}] Procesando JRV ${mesa.numero}...`);

                        try {
                            // Obtener votos, actas, votos nulos y votos en blanco de esta JRV
                            const [votos, actas, votosBlanco, votosNulos] = await Promise.all([
                                obtenerVotosJRV(depto.id_departamento, muni.id_municipio, zona.id_zona, puesto.id_puesto, mesa.numero),
                                obtenerActasJRV(depto.id_departamento, muni.id_municipio, zona.id_zona, puesto.id_puesto, mesa.numero),
                                obtenerVotosBlanco(depto.id_departamento, muni.id_municipio, zona.id_zona, puesto.id_puesto, mesa.numero),
                                obtenerVotosNulos(depto.id_departamento, muni.id_municipio, zona.id_zona, puesto.id_puesto, mesa.numero)
                            ]);

                            // Extraer votos de TODOS los partidos
                            let votosDC = 0;              // Partido Demócrata Cristiano (0001)
                            let votosLibre = 0;           // Partido Libertad y Refundación (0002)
                            let votosPinu = 0;            // Partido Innovación y Unidad (0003)
                            let votosLiberal = 0;         // Partido Liberal (0004)
                            let votosNacional = 0;        // Partido Nacional (0005)

                            if (votos && votos.candidatos) {
                                const dc = votos.candidatos.find(c => c.parpo_id === "0001");
                                const libre = votos.candidatos.find(c => c.parpo_id === "0002");
                                const pinu = votos.candidatos.find(c => c.parpo_id === "0003");
                                const liberal = votos.candidatos.find(c => c.parpo_id === "0004");
                                const nacional = votos.candidatos.find(c => c.parpo_id === "0005");

                                votosDC = dc ? dc.votos : 0;
                                votosLibre = libre ? libre.votos : 0;
                                votosPinu = pinu ? pinu.votos : 0;
                                votosLiberal = liberal ? liberal.votos : 0;
                                votosNacional = nacional ? nacional.votos : 0;
                            }

                            // Calcular error de suma
                            const enEspera = actas?.espera || 0;
                            const correctas = actas?.correctas || 0;
                            const inconsistencias = actas?.inconsistencias || 0;
                            const sumaEstados = enEspera + correctas + inconsistencias;
                            const errorSuma = (sumaEstados !== 1) ? 1 : 0;

                            const resultado = {
                                id_departamento: depto.id_departamento,
                                departamento: depto.departamento,
                                id_municipio: muni.id_municipio,
                                municipio: muni.municipio,
                                id_zona: zona.id_zona,
                                zona: zona.zona,
                                id_puesto: puesto.id_puesto,
                                puesto: puesto.puesto,
                                numero_jrv: mesa.numero,
                                fecha_corte: votos?.fecha_corte ? votos.fecha_corte.substring(0, 16) : "",
                                votos_dc: votosDC,
                                votos_libre: votosLibre,
                                votos_pinu: votosPinu,
                                votos_liberal: votosLiberal,
                                votos_nacional: votosNacional,
                                votos_nulos: votosNulos,
                                votos_blanco: votosBlanco,
                                cantidad_total_actas: actas?.total || 0,
                                verificado: actas?.verificacion || 0,
                                cantidad_inconsistencias: actas?.inconsistencias || 0,
                                publicado: actas?.publicadas || 0,
                                en_espera: actas?.espera || 0,
                                correctas: actas?.correctas || 0,
                                inconsistencias: actas?.inconsistencias || 0,
                                error_suma: errorSuma,
                                etiquetas: mesa.etiquetas ? mesa.etiquetas.join(', ') : "",
                                url_acta_pdf: mesa.nombre_archivo || ""
                            };

                            resultados.push(resultado);
                            totalJRVs++;

                            // Mostrar resumen de la JRV procesada
                            const totalVotos = votosDC + votosLibre + votosPinu + votosLiberal + votosNacional + votosNulos + votosBlanco;
                            console.log(`            ✅ JRV ${mesa.numero}: L=${votosLiberal}, N=${votosNacional}, LIBRE=${votosLibre}, PINU=${votosPinu}, DC=${votosDC}, Nulos=${votosNulos}, Blanco=${votosBlanco}, Total=${totalVotos}`);

                        } catch (error) {
                            console.error(`            ❌ Error procesando JRV ${mesa.numero}:`, error);
                            errorCount++;
                        }

                        // Esperar entre JRVs (importante para no saturar)
                        await esperar(400);
                    }

                    // Esperar entre centros de votación
                    await esperar(500);
                }

                // Esperar entre zonas
                await esperar(700);
            }

            // Esperar entre municipios
            await esperar(1000);

            // Guardar progreso cada 10 municipios
            if ((j + 1) % 10 === 0) {
                console.log(`\n💾 Auto-guardado de progreso (${totalJRVs} JRVs procesadas hasta ahora)...`);
                window.resultadosCNEDetallados = resultados;
            }
        }

        // Esperar entre departamentos
        await esperar(2000);
    }

    console.log(`\n${"=".repeat(80)}`);
    console.log(`✅ ¡EXTRACCIÓN COMPLETADA!`);
    console.log(`${"=".repeat(80)}`);
    console.log(`📊 Total JRVs procesadas: ${totalJRVs}`);
    console.log(`❌ Errores encontrados: ${errorCount}`);
    console.log(`\n💾 Para descargar el JSON, ejecuta:`);
    console.log(`descargarJSON(resultados);`);
    console.log(`${"=".repeat(80)}\n`);

    // Guardar en variable global para poder descargarlo
    window.resultadosCNEDetallados = resultados;

    return resultados;
}

// Función para descargar el JSON
function descargarJSON(datos) {
    const dataStr = JSON.stringify(datos, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
    link.download = `resultados_jrv_detallado_${timestamp}.json`;
    link.click();
    URL.revokeObjectURL(url);
    console.log(`✅ Archivo descargado: resultados_jrv_detallado_${timestamp}.json`);
}

// Función para ver progreso
function verProgreso() {
    if (window.resultadosCNEDetallados) {
        console.log(`📊 JRVs procesadas hasta ahora: ${window.resultadosCNEDetallados.length}`);
        console.log(`📥 Para descargar: descargarJSON(window.resultadosCNEDetallados)`);

        // Mostrar resumen por departamento
        const porDepto = {};
        window.resultadosCNEDetallados.forEach(r => {
            if (!porDepto[r.departamento]) {
                porDepto[r.departamento] = 0;
            }
            porDepto[r.departamento]++;
        });

        console.log("\n📈 Resumen por departamento:");
        Object.entries(porDepto).forEach(([depto, count]) => {
            console.log(`   ${depto}: ${count} JRVs`);
        });
    } else {
        console.log("⚠️ Aún no hay datos. Ejecuta primero: await extraerTodosLosDatosDetallados()");
    }
}

// Función para extraer solo un departamento específico
async function extraerUnDepartamento(idDepartamento) {
    const depto = DEPARTAMENTOS.find(d => d.id_departamento === idDepartamento);

    if (!depto) {
        console.error(`❌ Departamento ${idDepartamento} no encontrado`);
        return [];
    }

    console.log(`🚀 Extrayendo solo: ${depto.departamento} (${depto.id_departamento})\n`);

    // Crear una copia temporal para procesar solo este departamento
    const deptoTemp = [depto];
    const DEPARTAMENTOS_ORIGINAL = [...DEPARTAMENTOS];

    // Reemplazar temporalmente
    DEPARTAMENTOS.length = 0;
    DEPARTAMENTOS.push(depto);

    const resultados = await extraerTodosLosDatosDetallados();

    // Restaurar
    DEPARTAMENTOS.length = 0;
    DEPARTAMENTOS.push(...DEPARTAMENTOS_ORIGINAL);

    return resultados;
}

// Función para extraer solo un municipio específico
async function extraerUnMunicipio(idDepartamento, idMunicipio) {
    const depto = DEPARTAMENTOS.find(d => d.id_departamento === idDepartamento);

    if (!depto) {
        console.error(`❌ Departamento ${idDepartamento} no encontrado`);
        return [];
    }

    console.log(`🚀 Extrayendo municipio específico...`);
    console.log(`📍 Departamento: ${depto.departamento} (${depto.id_departamento})`);
    console.log(`🏘️  Municipio: ${idMunicipio}\n`);

    const resultados = [];
    let totalJRVs = 0;
    let errorCount = 0;

    // Obtener información del municipio
    const municipios = await obtenerMunicipios(depto.id_departamento);
    const muni = municipios.find(m => m.id_municipio === idMunicipio);

    if (!muni) {
        console.error(`❌ Municipio ${idMunicipio} no encontrado en el departamento ${depto.departamento}`);
        return [];
    }

    console.log(`✅ Municipio encontrado: ${muni.municipio}`);
    console.log(`${"=".repeat(80)}\n`);

    // Obtener zonas del municipio
    const zonas = await obtenerZonas(depto.id_departamento, muni.id_municipio);
    console.log(`📍 ${zonas.length} zona(s) encontrada(s): ${zonas.map(z => z.zona).join(', ')}`);
    await esperar(300);

    for (let k = 0; k < zonas.length; k++) {
        const zona = zonas[k];
        console.log(`\n🌍 [${k + 1}/${zonas.length}] ZONA: ${zona.zona} (${zona.id_zona})`);

        // Obtener centros de votación (puestos) de la zona
        const puestos = await obtenerPuestos(depto.id_departamento, muni.id_municipio, zona.id_zona);
        console.log(`   🏢 ${puestos.length} centro(s) de votación encontrado(s)`);
        await esperar(300);

        for (let l = 0; l < puestos.length; l++) {
            const puesto = puestos[l];
            console.log(`\n   📦 [${l + 1}/${puestos.length}] CENTRO: ${puesto.puesto.substring(0, 50)}${puesto.puesto.length > 50 ? '...' : ''}`);

            // Obtener mesas (JRVs) del centro de votación
            const mesas = await obtenerMesas(depto.id_departamento, muni.id_municipio, zona.id_zona, puesto.id_puesto);
            console.log(`      🗳️  ${mesas.length} JRV(s) encontrada(s)`);
            await esperar(200);

            for (let m = 0; m < mesas.length; m++) {
                const mesa = mesas[m];

                // Verificar si esta JRV ya está en Drive (excluir)
                if (JRVS_A_EXCLUIR.has(String(mesa.numero))) {
                    console.log(`      ✅ JRV ${mesa.numero}: Ya tiene URL en Drive, omitiendo...`);
                    continue;
                }

                // Solo procesar mesas publicadas
                if (mesa.publicada === 0) {
                    console.log(`      ⏭️  JRV ${mesa.numero}: Sin publicar, omitiendo...`);
                    continue;
                }

                console.log(`      ⚙️  [${m + 1}/${mesas.length}] Procesando JRV ${mesa.numero}...`);

                try {
                    // Obtener votos, actas, votos nulos y votos en blanco de esta JRV
                    const [votos, actas, votosBlanco, votosNulos] = await Promise.all([
                        obtenerVotosJRV(depto.id_departamento, muni.id_municipio, zona.id_zona, puesto.id_puesto, mesa.numero),
                        obtenerActasJRV(depto.id_departamento, muni.id_municipio, zona.id_zona, puesto.id_puesto, mesa.numero),
                        obtenerVotosBlanco(depto.id_departamento, muni.id_municipio, zona.id_zona, puesto.id_puesto, mesa.numero),
                        obtenerVotosNulos(depto.id_departamento, muni.id_municipio, zona.id_zona, puesto.id_puesto, mesa.numero)
                    ]);

                    // Extraer votos de TODOS los partidos
                    let votosDC = 0;              // Partido Demócrata Cristiano (0001)
                    let votosLibre = 0;           // Partido Libertad y Refundación (0002)
                    let votosPinu = 0;            // Partido Innovación y Unidad (0003)
                    let votosLiberal = 0;         // Partido Liberal (0004)
                    let votosNacional = 0;        // Partido Nacional (0005)

                    if (votos && votos.candidatos) {
                        const dc = votos.candidatos.find(c => c.parpo_id === "0001");
                        const libre = votos.candidatos.find(c => c.parpo_id === "0002");
                        const pinu = votos.candidatos.find(c => c.parpo_id === "0003");
                        const liberal = votos.candidatos.find(c => c.parpo_id === "0004");
                        const nacional = votos.candidatos.find(c => c.parpo_id === "0005");

                        votosDC = dc ? dc.votos : 0;
                        votosLibre = libre ? libre.votos : 0;
                        votosPinu = pinu ? pinu.votos : 0;
                        votosLiberal = liberal ? liberal.votos : 0;
                        votosNacional = nacional ? nacional.votos : 0;
                    }

                    // Calcular error de suma
                    const enEspera = actas?.espera || 0;
                    const correctas = actas?.correctas || 0;
                    const inconsistencias = actas?.inconsistencias || 0;
                    const sumaEstados = enEspera + correctas + inconsistencias;
                    const errorSuma = (sumaEstados !== 1) ? 1 : 0;

                    const resultado = {
                        id_departamento: depto.id_departamento,
                        departamento: depto.departamento,
                        id_municipio: muni.id_municipio,
                        municipio: muni.municipio,
                        id_zona: zona.id_zona,
                        zona: zona.zona,
                        id_puesto: puesto.id_puesto,
                        puesto: puesto.puesto,
                        numero_jrv: mesa.numero,
                        fecha_corte: votos?.fecha_corte ? votos.fecha_corte.substring(0, 16) : "",
                        votos_dc: votosDC,
                        votos_libre: votosLibre,
                        votos_pinu: votosPinu,
                        votos_liberal: votosLiberal,
                        votos_nacional: votosNacional,
                        votos_nulos: votosNulos,
                        votos_blanco: votosBlanco,
                        cantidad_total_actas: actas?.total || 0,
                        verificado: actas?.verificacion || 0,
                        cantidad_inconsistencias: actas?.inconsistencias || 0,
                        publicado: actas?.publicadas || 0,
                        en_espera: actas?.espera || 0,
                        correctas: actas?.correctas || 0,
                        inconsistencias: actas?.inconsistencias || 0,
                        error_suma: errorSuma,
                        etiquetas: mesa.etiquetas ? mesa.etiquetas.join(', ') : "",
                        url_acta_pdf: mesa.nombre_archivo || ""
                    };

                    resultados.push(resultado);
                    totalJRVs++;

                    // Mostrar resumen de la JRV procesada
                    const totalVotos = votosDC + votosLibre + votosPinu + votosLiberal + votosNacional + votosNulos + votosBlanco;
                    console.log(`      ✅ JRV ${mesa.numero}: L=${votosLiberal}, N=${votosNacional}, LIBRE=${votosLibre}, PINU=${votosPinu}, DC=${votosDC}, Nulos=${votosNulos}, Blanco=${votosBlanco}, Total=${totalVotos}`);

                } catch (error) {
                    console.error(`      ❌ Error procesando JRV ${mesa.numero}:`, error);
                    errorCount++;
                }

                // Esperar entre JRVs (importante para no saturar)
                await esperar(400);
            }

            // Esperar entre centros de votación
            await esperar(500);
        }

        // Esperar entre zonas
        await esperar(700);
    }

    console.log(`\n${"=".repeat(80)}`);
    console.log(`✅ ¡EXTRACCIÓN COMPLETADA!`);
    console.log(`${"=".repeat(80)}`);
    console.log(`📊 Municipio: ${muni.municipio}`);
    console.log(`📊 Total JRVs procesadas: ${totalJRVs}`);
    console.log(`❌ Errores encontrados: ${errorCount}`);
    console.log(`\n💾 Para descargar el JSON, ejecuta:`);
    console.log(`descargarJSON(resultados);`);
    console.log(`${"=".repeat(80)}\n`);

    // Guardar en variable global para poder descargarlo
    window.resultadosCNEDetallados = resultados;

    return resultados;
}

// Función para extraer solo un centro de votación específico
// Ejemplo: extraerUnCentroVotacion("18", "003", "02", "007")
// Esto extrae: Yoro > El Negrito > Rural > EL JUNCO - ESC. CRISTOBAL COLON
async function extraerUnCentroVotacion(idDepartamento, idMunicipio, idZona, idPuesto) {
    const depto = DEPARTAMENTOS.find(d => d.id_departamento === idDepartamento);

    if (!depto) {
        console.error(`❌ Departamento ${idDepartamento} no encontrado`);
        return [];
    }

    console.log(`🚀 Extrayendo centro de votación específico...`);
    console.log(`📍 Departamento: ${depto.departamento} (${depto.id_departamento})`);
    console.log(`🏘️  Municipio: ${idMunicipio}`);
    console.log(`🌍 Zona: ${idZona}`);
    console.log(`📦 Centro de Votación: ${idPuesto}\n`);

    const resultados = [];
    let totalJRVs = 0;
    let errorCount = 0;

    // Obtener información del municipio
    const municipios = await obtenerMunicipios(depto.id_departamento);
    const muni = municipios.find(m => m.id_municipio === idMunicipio);

    if (!muni) {
        console.error(`❌ Municipio ${idMunicipio} no encontrado en el departamento ${depto.departamento}`);
        return [];
    }

    console.log(`✅ Municipio encontrado: ${muni.municipio}`);

    // Obtener zonas del municipio
    const zonas = await obtenerZonas(depto.id_departamento, muni.id_municipio);
    const zona = zonas.find(z => z.id_zona === idZona);

    if (!zona) {
        console.error(`❌ Zona ${idZona} no encontrada. Zonas disponibles: ${zonas.map(z => `${z.id_zona}=${z.zona}`).join(', ')}`);
        return [];
    }

    console.log(`✅ Zona encontrada: ${zona.zona}`);

    // Obtener centros de votación (puestos) de la zona
    const puestos = await obtenerPuestos(depto.id_departamento, muni.id_municipio, zona.id_zona);
    const puesto = puestos.find(p => p.id_puesto === idPuesto);

    if (!puesto) {
        console.error(`❌ Centro de votación ${idPuesto} no encontrado`);
        console.log(`\n📋 Centros disponibles en ${zona.zona}:`);
        puestos.forEach(p => {
            console.log(`   ${p.id_puesto}: ${p.puesto}`);
        });
        return [];
    }

    console.log(`✅ Centro de votación encontrado: ${puesto.puesto}`);
    console.log(`${"=".repeat(80)}\n`);

    // Obtener mesas (JRVs) del centro de votación
    const mesas = await obtenerMesas(depto.id_departamento, muni.id_municipio, zona.id_zona, puesto.id_puesto);
    console.log(`🗳️  ${mesas.length} JRV(s) encontrada(s) en este centro`);
    console.log(`${"=".repeat(80)}\n`);
    await esperar(200);

    for (let m = 0; m < mesas.length; m++) {
        const mesa = mesas[m];

        // Verificar si esta JRV ya está en Drive (excluir)
        if (JRVS_A_EXCLUIR.has(String(mesa.numero))) {
            console.log(`✅ JRV ${mesa.numero}: Ya tiene URL en Drive, omitiendo...`);
            continue;
        }

        // Solo procesar mesas publicadas
        if (mesa.publicada === 0) {
            console.log(`⏭️  JRV ${mesa.numero}: Sin publicar, omitiendo...`);
            continue;
        }

        console.log(`⚙️  [${m + 1}/${mesas.length}] Procesando JRV ${mesa.numero}...`);

        try {
            // Obtener votos, actas, votos nulos y votos en blanco de esta JRV
            const [votos, actas, votosBlanco, votosNulos] = await Promise.all([
                obtenerVotosJRV(depto.id_departamento, muni.id_municipio, zona.id_zona, puesto.id_puesto, mesa.numero),
                obtenerActasJRV(depto.id_departamento, muni.id_municipio, zona.id_zona, puesto.id_puesto, mesa.numero),
                obtenerVotosBlanco(depto.id_departamento, muni.id_municipio, zona.id_zona, puesto.id_puesto, mesa.numero),
                obtenerVotosNulos(depto.id_departamento, muni.id_municipio, zona.id_zona, puesto.id_puesto, mesa.numero)
            ]);

            // Extraer votos de TODOS los partidos
            let votosDC = 0;              // Partido Demócrata Cristiano (0001)
            let votosLibre = 0;           // Partido Libertad y Refundación (0002)
            let votosPinu = 0;            // Partido Innovación y Unidad (0003)
            let votosLiberal = 0;         // Partido Liberal (0004)
            let votosNacional = 0;        // Partido Nacional (0005)

            if (votos && votos.candidatos) {
                const dc = votos.candidatos.find(c => c.parpo_id === "0001");
                const libre = votos.candidatos.find(c => c.parpo_id === "0002");
                const pinu = votos.candidatos.find(c => c.parpo_id === "0003");
                const liberal = votos.candidatos.find(c => c.parpo_id === "0004");
                const nacional = votos.candidatos.find(c => c.parpo_id === "0005");

                votosDC = dc ? dc.votos : 0;
                votosLibre = libre ? libre.votos : 0;
                votosPinu = pinu ? pinu.votos : 0;
                votosLiberal = liberal ? liberal.votos : 0;
                votosNacional = nacional ? nacional.votos : 0;
            }

            // Calcular error de suma
            const enEspera = actas?.espera || 0;
            const correctas = actas?.correctas || 0;
            const inconsistencias = actas?.inconsistencias || 0;
            const sumaEstados = enEspera + correctas + inconsistencias;
            const errorSuma = (sumaEstados !== 1) ? 1 : 0;

            const resultado = {
                id_departamento: depto.id_departamento,
                departamento: depto.departamento,
                id_municipio: muni.id_municipio,
                municipio: muni.municipio,
                id_zona: zona.id_zona,
                zona: zona.zona,
                id_puesto: puesto.id_puesto,
                puesto: puesto.puesto,
                numero_jrv: mesa.numero,
                fecha_corte: votos?.fecha_corte ? votos.fecha_corte.substring(0, 16) : "",
                votos_dc: votosDC,
                votos_libre: votosLibre,
                votos_pinu: votosPinu,
                votos_liberal: votosLiberal,
                votos_nacional: votosNacional,
                votos_nulos: votosNulos,
                votos_blanco: votosBlanco,
                cantidad_total_actas: actas?.total || 0,
                verificado: actas?.verificacion || 0,
                cantidad_inconsistencias: actas?.inconsistencias || 0,
                publicado: actas?.publicadas || 0,
                en_espera: actas?.espera || 0,
                correctas: actas?.correctas || 0,
                inconsistencias: actas?.inconsistencias || 0,
                error_suma: errorSuma,
                etiquetas: mesa.etiquetas ? mesa.etiquetas.join(', ') : "",
                url_acta_pdf: mesa.nombre_archivo || ""
            };

            resultados.push(resultado);
            totalJRVs++;

            // Mostrar resumen de la JRV procesada
            const totalVotos = votosDC + votosLibre + votosPinu + votosLiberal + votosNacional + votosNulos + votosBlanco;
            console.log(`✅ JRV ${mesa.numero}: L=${votosLiberal}, N=${votosNacional}, LIBRE=${votosLibre}, PINU=${votosPinu}, DC=${votosDC}, Nulos=${votosNulos}, Blanco=${votosBlanco}, Total=${totalVotos}\n`);

        } catch (error) {
            console.error(`❌ Error procesando JRV ${mesa.numero}:`, error);
            errorCount++;
        }

        // Esperar entre JRVs
        await esperar(400);
    }

    console.log(`\n${"=".repeat(80)}`);
    console.log(`✅ ¡EXTRACCIÓN COMPLETADA!`);
    console.log(`${"=".repeat(80)}`);
    console.log(`📍 Departamento: ${depto.departamento}`);
    console.log(`🏘️  Municipio: ${muni.municipio}`);
    console.log(`🌍 Zona: ${zona.zona}`);
    console.log(`📦 Centro: ${puesto.puesto}`);
    console.log(`📊 Total JRVs procesadas: ${totalJRVs}`);
    console.log(`❌ Errores encontrados: ${errorCount}`);
    console.log(`\n💾 Para descargar el JSON, ejecuta:`);
    console.log(`descargarJSON(resultados);`);
    console.log(`${"=".repeat(80)}\n`);

    // Guardar en variable global para poder descargarlo
    window.resultadosCNEDetallados = resultados;

    return resultados;
}

// ========================================
// INSTRUCCIONES DE USO
// ========================================
console.log(`
╔════════════════════════════════════════════════════════════════════════╗
║  SCRIPT DE EXTRACCIÓN DETALLADA COMPLETA DE DATOS DEL CNE (POR JRV) ║
║       Incluye TODOS los partidos + Votos Nulos + Votos en Blanco     ║
╚════════════════════════════════════════════════════════════════════════╝

📋 INSTRUCCIONES:

1. Asegúrate de estar en: https://resultadosgenerales2025.cne.hn
2. Abre la consola del navegador (F12 > Console)
3. Copia y pega este script completo
4. Ejecuta el siguiente comando:

   await extraerTodosLosDatosDetallados()

5. ⚠️ IMPORTANTE: Este proceso puede tardar VARIAS HORAS
   (Hay aproximadamente 20,000+ JRVs en todo Honduras)

6. ☕ Ve por café, deja ejecutando y NO cierres la pestaña
7. Cuando termine, descarga el JSON con:

   descargarJSON(window.resultadosCNEDetallados)

📊 COMANDOS DISPONIBLES:

- extraerTodosLosDatosDetallados()              : Extrae TODAS las JRVs
- extraerUnDepartamento("05")                   : Extrae solo un departamento
- extraerUnMunicipio("18", "003")               : Extrae solo un municipio específico
- extraerUnCentroVotacion("18", "003", "02", "007")  : Extrae solo un centro de votación
- verProgreso()                                 : Ver cuántas JRVs procesadas
- descargarJSON(datos)                          : Descargar el JSON

💡 RECOMENDACIONES:

1. Si es tu primera vez, prueba con UN CENTRO DE VOTACIÓN pequeño (MÁS RÁPIDO):
   await extraerUnCentroVotacion("18", "003", "02", "007")
   // Yoro, El Negrito, Rural, EL JUNCO - ESC. CRISTOBAL COLON

2. O prueba con un municipio pequeño:
   await extraerUnMunicipio("18", "003")  // El Negrito, Yoro

3. O prueba con un departamento pequeño:
   await extraerUnDepartamento("11")  // Islas de la Bahía

2. Para procesar todo, mejor hazlo de noche o cuando no uses la PC

3. El script auto-guarda cada 10 municipios en window.resultadosCNEDetallados

4. Si se interrumpe, puedes descargar lo procesado hasta el momento:
   descargarJSON(window.resultadosCNEDetallados)

5. Mantén esta pestaña como ACTIVA (no la minimices completamente)

⚠️ CÓDIGOS DE DEPARTAMENTOS:
01=Atlántida, 02=Colón, 03=Comayagua, 04=Copán, 05=Cortés
06=Choluteca, 07=El Paraíso, 08=Francisco Morazán, 09=Gracias a Dios
10=Intibucá, 11=Islas de la Bahía, 12=La Paz, 13=Lempira
14=Ocotepeque, 15=Olancho, 16=Santa Bárbara, 17=Valle, 18=Yoro
20=Voto en el Exterior

🎯 PARTIDOS INCLUIDOS EN EL JSON:
- votos_dc      : Partido Demócrata Cristiano de Honduras (0001)
- votos_libre   : Partido Libertad y Refundación (0002)
- votos_pinu    : Partido Innovación y Unidad Social Demócrata (0003)
- votos_liberal : Partido Liberal de Honduras (0004)
- votos_nacional: Partido Nacional de Honduras (0005)
- votos_nulos   : Votos nulos
- votos_blanco  : Votos en blanco

🚀 ¡Listo! Ahora ejecuta el comando que prefieras
`);
