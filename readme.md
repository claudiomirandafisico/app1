# Suite de Calculo Electrico: Dimensionamiento de Conductores, Caida de Tension y Protecciones

Herramienta computacional en Python para el dimensionamiento de alimentadores y circuitos de baja tensión bajo criterios de capacidad térmica de transporte, regulación de tensión por impedancia y coordinación de protecciones termomagnéticas (Pliegos Técnicos Normativos RIC N°03 y N°04 SEC / IEC 60364).

## Características Técnicas

1. **Cálculo Exacto de Caída de Tensión por Impedancia:**
   - Corrección automática de la resistividad eléctrica $\rho_T$ según el material (Cobre o Aluminio) y la temperatura máxima de régimen del aislamiento ($70\,^\circ\text{C}$ para PVC/THHN o $90\,^\circ\text{C}$ para XLPE/EPR/RZ1-K).
   - Incorporación de la componente reactiva inductiva ($X_L \sin\varphi$) además de la resistencia activa ($R \cos\varphi$).
2. **Factores de Corrección (Derating):**
   - Ajuste dinámico de la ampacidad admisible $I_Z'$ por temperatura ambiente y por agrupamiento de circuitos en ductos o bandejas portaconductores.
3. **Coordinación de Protecciones y Cortocircuito:**
   - Selección comercial de interruptores termomagnéticos (Curvas B, C y D) verificando la desigualdad normativa $I_B \le I_n \le I_Z'$ y $I_2 \le 1.45 I_Z'$.
   - Cálculo de la corriente máxima de cortocircuito soportada adiabáticamente por el conductor ($I_{cc} = k \cdot S / \sqrt{t}$).
4. **Exportación de Entregables de Ingeniería:**
   - Generación automática de la **Memoria de Cálculo Técnico (.MD)** con ecuaciones en $\LaTeX$ y exportación de la matriz completa de secciones en **CSV**.

## Instalación y Ejecución

```bash
git clone [https://github.com/TU_USUARIO/electrical-engineering-calc-suite.git](https://github.com/TU_USUARIO/electrical-engineering-calc-suite.git)
cd electrical-engineering-calc-suite
pip install -r requirements.txt
streamlit run app.py