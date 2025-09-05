# Modelo de Optimización para Asignación de Técnicos

## Conjuntos

- $J$ = Conjunto de trabajos ${j_1, j_2, ..., j_n}$
- $T$ = Conjunto de técnicos ${t_1, t_2, ..., t_m}$

## Parámetros

- $p_j$ = Duración del trabajo $j$ (horas)
- $q_{jt}$ = 1 si técnico $t$ tiene skill para $j$, 0 si no
- $H_t$ = Capacidad diaria del técnico $t$ (horas/día)
- $D$ = Días en horizonte (7 días)

## Variables de decisión

- $x_{jt} \in \{0,1\}$ = 1 si trabajo $j$ asignado a técnico $t$
- $L \geq 0$ = Carga máxima entre técnicos

## Función objetivo

$$\min Z = L$$

## Restricciones

1. **Asignación única**: $\sum_{t \in T} x_{jt} = 1 \quad \forall j \in J$
2. **Compatibilidad**: $x_{jt} \leq q_{jt} \quad \forall j \in J, \forall t \in T$
3. **Balance carga**: $\sum_{j \in J} p_j \cdot x_{jt} \leq L \quad \forall t \in T$
4. **Capacidad**: $\sum_{j \in J} p_j \cdot x_{jt} \leq H_t \cdot D \quad \forall t \in T$
