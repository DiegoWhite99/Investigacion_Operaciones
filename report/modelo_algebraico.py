"""
Verificación del Modelo Algebraico
"""


def mostrar_modelo():
    print("""
    MODELO ALGEBRAICO - ASIGNACIÓN DE TÉCNICOS
    ------------------------------------------
    
    Conjuntos:
    J = {j1, j2, ..., jn}  # Trabajos
    T = {t1, t2, ..., tm}  # Técnicos
    
    Parámetros:
    p_j = duración trabajo j (horas)
    q_jt = 1 si técnico t tiene skill para j
    H_t = capacidad diaria técnico t (horas/día)
    D = días horizonte = 7
    
    Variables de decisión:
    x_jt ∈ {0,1}  # 1 si trabajo j asignado a técnico t
    L ≥ 0          # Carga máxima (horas)
    
    Función objetivo:
    min Z = L
    
    Restricciones:
    1. ∑x_jt = 1 ∀j ∈ J          (Cada trabajo a un técnico)
    2. x_jt ≤ q_jt ∀j ∈ J, ∀t ∈ T (Solo técnicos calificados)
    3. ∑p_j·x_jt ≤ L ∀t ∈ T      (Balance de carga)
    4. ∑p_j·x_jt ≤ H_t·D ∀t ∈ T  (Respetar capacidad)
    """)


if __name__ == "__main__":
    mostrar_modelo()
