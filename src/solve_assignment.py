import time
from datetime import datetime
import os
import pandas as pd
import pulp

print("=== IMPLEMENTACIÓN DEL MODELO DE ASIGNACIÓN ===")
print("Iniciando proceso...")
start_time = time.time()

# =========================
# 1. CARGAR DATOS LIMPIOS
# =========================
base_path = os.path.dirname(os.path.abspath(__file__))  # directorio del script

paths = {
    'jobs': os.path.join(base_path, "../data/clean/jobs_clean.csv"),
    'tecnicos': os.path.join(base_path, "../data/clean/tecnicos_clean.csv"),
    'habilidades': os.path.join(base_path, "../data/clean/habilidades_clean.csv")
}

# Verificar existencia de archivos
for name, path in paths.items():
    if not os.path.exists(path):
        raise FileNotFoundError(f"Archivo '{name}' no encontrado en {path}")

# Cargar CSVs
jobs = pd.read_csv(paths['jobs'])
tecnicos = pd.read_csv(paths['tecnicos'])
habilidades = pd.read_csv(paths['habilidades'])

# =========================
# Normalizar nombres de columnas
# =========================
tecnicos.rename(columns=lambda x: x.strip(), inplace=True)  # eliminar espacios
tecnicos.rename(columns={'Id_tecnico': 'id_tecnico'},
                inplace=True)  # normalizar
jobs.rename(columns=lambda x: x.strip(), inplace=True)
habilidades.rename(columns=lambda x: x.strip(), inplace=True)

# Validar columnas críticas
required_cols = {
    'jobs': ['id_job', 'duracion_horas', 'skill_requerida'],
    'tecnicos': ['id_tecnico', 'capacidad_diaria_h'],
    'habilidades': ['id_job', 'id_tecnico', 'compatible']
}

dataframes = {'jobs': jobs, 'tecnicos': tecnicos, 'habilidades': habilidades}
for df_name, cols in required_cols.items():
    missing = set(cols) - set(dataframes[df_name].columns)
    if missing:
        raise ValueError(f"Faltan columnas en {df_name}: {missing}")

print("1. Datos cargados correctamente.")

# =========================
# 2. PREPARAR PARÁMETROS
# =========================
print("2. Preparando parámetros...")

J = jobs['id_job'].tolist()
T = tecnicos['id_tecnico'].tolist()

# Diccionarios
p = jobs.set_index('id_job')['duracion_horas'].to_dict()
H = (tecnicos.set_index('id_tecnico')['capacidad_diaria_h'] * 7).to_dict()
q = {(row['id_job'], row['id_tecnico']): row['compatible']
     for _, row in habilidades.iterrows()}

# =========================
# 3. CREAR MODELO DE OPTIMIZACIÓN
# =========================
print("3. Creando modelo de optimización...")

prob = pulp.LpProblem("AsignacionOptimaTecnicos", pulp.LpMinimize)

# Variables de decisión
x = pulp.LpVariable.dicts("x", [(j, t) for j in J for t in T], cat='Binary')
L = pulp.LpVariable("L", lowBound=0, cat='Continuous')

# Función objetivo: minimizar la carga máxima
prob += L, "Minimizar_Carga_Maxima"

# =========================
# 4. RESTRICCIONES
# =========================

# 4.1 Asignación única: cada trabajo a un técnico
for j in J:
    prob += pulp.lpSum(x[(j, t)] for t in T) == 1, f"Asignacion_Unica_{j}"

# 4.2 Compatibilidad de habilidades
for (j, t), comp in q.items():
    prob += x[(j, t)] <= comp, f"Compatibilidad_{j}_{t}"

# 4.3 Balance de carga: cada técnico ≤ L
for t in T:
    prob += pulp.lpSum(p[j] * x[(j, t)] for j in J) <= L, f"Balance_Carga_{t}"

# 4.4 Capacidad máxima de cada técnico
for t in T:
    prob += pulp.lpSum(p[j] * x[(j, t)] for j in J) <= H[t], f"Capacidad_{t}"

# =========================
# 5. RESOLVER MODELO
# =========================
print("4. Resolviendo modelo...")
solver = pulp.PULP_CBC_CMD(msg=True, timeLimit=300)
prob.solve(solver)

# =========================
# 6. ANALIZAR RESULTADOS
# =========================
print("5. Resultados:")
print(f"Status: {pulp.LpStatus[prob.status]}")
print(f"Carga máxima L: {pulp.value(L):.2f} horas")

# =========================
# 7. GUARDAR ASIGNACIONES
# =========================
resultados = []
cargas_tecnicos = {}

for t in T:
    carga_actual = 0
    for j in J:
        if pulp.value(x[(j, t)]) == 1:
            skill = jobs.loc[jobs['id_job'] == j, 'skill_requerida'].values[0]
            resultados.append({
                'job_id': j,
                'tecnico_id': t,
                'duracion_horas': p[j],
                'skill_requerida': skill
            })
            carga_actual += p[j]
    cargas_tecnicos[t] = carga_actual

resultados_df = pd.DataFrame(resultados)

# Merge con información de técnicos
tecnicos_cols = (
    ['id_tecnico', 'nombre', 'capacidad_diaria_h']
    if 'nombre' in tecnicos.columns
    else ['id_tecnico', 'capacidad_diaria_h']
)
resultados_df = resultados_df.merge(
    tecnicos[tecnicos_cols], left_on='tecnico_id', right_on='id_tecnico', how='left')

# Guardar CSVs
results_folder = os.path.join(base_path, "../results")
os.makedirs(results_folder, exist_ok=True)

resultados_df.to_csv(os.path.join(
    results_folder, "assignment_results.csv"), index=False)
cargas_df = pd.DataFrame(list(cargas_tecnicos.items()), columns=[
                         'tecnico_id', 'carga_total_horas'])
cargas_df.to_csv(os.path.join(
    results_folder, "tecnicos_carga.csv"), index=False)

# =========================
# 8. MOSTRAR RESUMEN
# =========================
print("\n=== RESUMEN FINAL ===")
print(f"Trabajos asignados: {len(resultados_df)}")
print(f"Técnicos utilizados: {len(cargas_df)}")
print(f"Carga máxima (L): {pulp.value(L):.2f} horas\n")

for t in T:
    carga = cargas_tecnicos.get(t, 0)
    capacidad = H.get(t, 0)
    utilizacion = (carga / capacidad) * 100 if capacidad > 0 else 0
    print(f"  {t}: {carga:.1f}h / {capacidad:.1f}h ({utilizacion:.1f}%)")

# =========================
# 9. GUARDAR LOG DE EJECUCIÓN
# =========================
end_time = time.time()
tiempo_ejecucion = end_time - start_time

log_path = os.path.join(results_folder, "ejecucion_log.txt")
with open(log_path, "w", encoding="utf-8") as f:
    f.write(f"Fecha ejecución: {datetime.now()}\n")
    f.write(f"Tiempo ejecución: {tiempo_ejecucion:.2f} segundos\n")
    f.write(f"Status: {pulp.LpStatus[prob.status]}\n")
    f.write(f"Valor objetivo: {pulp.value(L):.2f}\n")
    f.write(f"Trabajos asignados: {len(resultados_df)}\n")

print(f"\n✅ Proceso completado en {tiempo_ejecucion:.2f} segundos")
print(f"📍 Resultados guardados en: {results_folder}")
