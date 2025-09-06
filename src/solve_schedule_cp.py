from ortools.sat.python import cp_model
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
import matplotlib.pyplot as plt
import os

print("=== PLANIFICACIÓN AVANZADA CON OR-TOOLS CP-SAT ===")
print("Iniciando planificación con secuenciación...")

# Obtener ruta base del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1. CARGAR DATOS Y RESULTADOS PREVIOS
print("1. Cargando datos...")
try:
    jobs_path = os.path.join(BASE_DIR, "data", "clean", "jobs_clean.csv")
    tecnicos_path = os.path.join(
        BASE_DIR, "data", "clean", "tecnicos_clean.csv")
    asignaciones_path = os.path.join(
        BASE_DIR, "results", "assignment_results.csv")

    jobs = pd.read_csv(jobs_path)
    tecnicos = pd.read_csv(tecnicos_path)
    asignaciones = pd.read_csv(asignaciones_path)

    print(f"   ✅ Jobs cargados: {len(jobs)} registros")
    print(f"   ✅ Técnicos cargados: {len(tecnicos)} registros")
    print(f"   ✅ Asignaciones cargadas: {len(asignaciones)} registros")

except FileNotFoundError as e:
    print(f"   ❌ Error cargando archivos: {e}")
    print("   Ejecuta primero: python src/clean_data.py y python src/solve_assignment.py")
    exit()

# 2. CONFIGURACIÓN DEL HORIZONTE TEMPORAL
print("2. Configurando horizonte temporal...")
DIAS_HORIZONTE = 7
HORAS_POR_DIA = 8
HORIZONTE_MINUTOS = DIAS_HORIZONTE * HORAS_POR_DIA * 60

# Convertir duraciones a minutos
jobs['duracion_minutos'] = jobs['duracion_horas'] * 60

# 3. CREAR EL MODELO CP-SAT
print("3. Creando modelo CP-SAT...")
model = cp_model.CpModel()

# 4. VARIABLES DE DECISIÓN
print("4. Definiendo variables...")
start_vars = {}    # Hora de inicio de cada job
end_vars = {}      # Hora de fin de cada job
interval_vars = {}  # Variables de intervalo

print(f"   Procesando {len(jobs)} jobs...")

# CORRECCIÓN: Usar iterrows() correctamente
for index, row in jobs.iterrows():
    job_id = row['id_job']
    duracion = int(row['duracion_minutos'])

    # Debug: verificar los primeros 5 jobs
    if index < 5:
        print(
            f"     Creando variables para {job_id} (duración: {duracion} minutos)")

    # Variable de inicio (0 a horizonte)
    start_vars[job_id] = model.NewIntVar(
        0, HORIZONTE_MINUTOS, f'start_{job_id}')

    # Variable de fin
    end_vars[job_id] = model.NewIntVar(0, HORIZONTE_MINUTOS, f'end_{job_id}')

    # Variable de intervalo
    interval_vars[job_id] = model.NewIntervalVar(
        start_vars[job_id], duracion, end_vars[job_id], f'interval_{job_id}'
    )

# VERIFICACIÓN
print(f"   ✅ Intervalos creados: {len(interval_vars)}/{len(jobs)}")

# 5. RESTRICCIONES DE ASIGNACIÓN (CORREGIDO: Id_tecnico → Id_tecnico)
print("5. Añadiendo restricciones de asignación...")

# Verificar nombres de columnas en asignaciones
print(f"   Columnas en asignaciones: {asignaciones.columns.tolist()}")

# CORRECCIÓN: Usar 'Id_tecnico' en lugar de 'id_tecnico'
columna_tecnico = 'Id_tecnico' if 'Id_tecnico' in asignaciones.columns else 'id_tecnico'
columna_job = 'job_id' if 'job_id' in asignaciones.columns else 'id_job'

print(f"   Usando columna técnico: {columna_tecnico}")
print(f"   Usando columna job: {columna_job}")

# Agrupar jobs por técnico
jobs_por_tecnico = {}
jobs_procesados = 0
jobs_omitidos = 0

for _, asignacion in asignaciones.iterrows():
    # CORRECCIÓN: Usar el nombre correcto de la columna
    tecnico_id = asignacion[columna_tecnico]
    job_id = asignacion[columna_job]

    if job_id in interval_vars:
        if tecnico_id not in jobs_por_tecnico:
            jobs_por_tecnico[tecnico_id] = []
        jobs_por_tecnico[tecnico_id].append(interval_vars[job_id])
        jobs_procesados += 1
    else:
        print(f"   ⚠️  Job {job_id} no encontrado en interval_vars")
        jobs_omitidos += 1

print(f"   Jobs procesados: {jobs_procesados}")
print(f"   Jobs omitidos: {jobs_omitidos}")

# No overlap por técnico
for tecnico_id, intervals in jobs_por_tecnico.items():
    if intervals:
        model.AddNoOverlap(intervals)
        print(f"   Técnico {tecnico_id}: {len(intervals)} trabajos")

# 6. RESTRICCIONES DE VENTANAS TEMPORALES
print("6. Añadiendo restricciones de tiempo...")

# Convertir deadlines a minutos en el horizonte
for _, job in jobs.iterrows():
    job_id = job['id_job']
    deadline = pd.to_datetime(job['deadline'])
    dias_restantes = (deadline - datetime.now()).days

    # Limitar el inicio antes del deadline
    if dias_restantes >= 0:
        max_start = min(dias_restantes * HORAS_POR_DIA * 60, HORIZONTE_MINUTOS)
        model.Add(start_vars[job_id] <= max_start)

# 7. FUNCIÓN OBJETIVO
print("7. Definiendo función objetivo...")
makespan = model.NewIntVar(0, HORIZONTE_MINUTOS, 'makespan')
model.AddMaxEquality(makespan, list(end_vars.values()))
model.Minimize(makespan)

# 8. RESOLVER EL MODELO
print("8. Resolviendo el modelo...")
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 300.0

status = solver.Solve(model)

# 9. PROCESAR RESULTADOS
print("9. Procesando resultados...")
if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    print("✅ Solución encontrada!")

    # Recolectar resultados
    schedule_data = []

    for _, job in jobs.iterrows():
        job_id = job['id_job']
        if job_id not in start_vars:
            continue

        start_minutos = solver.Value(start_vars[job_id])
        end_minutos = solver.Value(end_vars[job_id])

        # Convertir a días y horas
        dia = (start_minutos // (HORAS_POR_DIA * 60)) + 1
        hora_inicio = (start_minutos % (HORAS_POR_DIA * 60)) // 60
        minuto_inicio = start_minutos % 60
        duracion = job['duracion_minutos'] / 60

        # Obtener técnico asignado (CORREGIDO: Usar columna correcta)
        tech_asignado = asignaciones[asignaciones[columna_job] == job_id]
        if not tech_asignado.empty:
            tecnico_id = tech_asignado.iloc[0][columna_tecnico]
        else:
            tecnico_id = "No asignado"

        schedule_data.append({
            'job_id': job_id,
            'descripcion': job['descripcion'],
            'tecnico_id': tecnico_id,
            'dia': dia,
            'hora_inicio': f"{int(hora_inicio):02d}:{int(minuto_inicio):02d}",
            'duracion_horas': duracion,
            'hora_fin': f"{int((end_minutos % (HORAS_POR_DIA * 60)) // 60):02d}:{int(end_minutos % 60):02d}",
            'skill_requerida': job['skill_requerida']
        })

    # 10. GUARDAR RESULTADOS
    print("10. Guardando resultados...")

    # Horario detallado
    schedule_df = pd.DataFrame(schedule_data)
    output_path = os.path.join(BASE_DIR, "results", "schedule_detailed.csv")
    schedule_df.to_csv(output_path, index=False)
    print(f"   📅 Horario guardado: {output_path}")

    # 11. MOSTRAR RESUMEN
    print("\n=== RESUMEN DE PLANIFICACIÓN ===")
    print(f"Trabajos planificados: {len(schedule_df)}")
    print(f"Días requeridos: {schedule_df['dia'].max()}")
    print(f"Técnicos utilizados: {len(schedule_df['tecnico_id'].unique())}")

    print("\n📋 Vista previa del horario:")
    print(schedule_df.head(10).to_string(index=False))

else:
    print("❌ No se encontró solución factible")

print("\n✅ Proceso de planificación completado!")
