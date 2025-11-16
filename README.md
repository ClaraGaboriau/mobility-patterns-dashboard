# 🧭 Mobility Patterns Dashboard

This repository contains the code developed for the **Bachelor Thesis project** titled  
**"Visualization of individual and global mobility patterns"**, completed at University of Fribourg (UNIFR).

The project implements an **interactive Streamlit web dashboard** for exploring and visualizing **mobility behaviors**.  
It is based on anonymized mobility data collected through the **SWICE (Sustainable Well-being for the Individual and the Collectivity in the Energy transition)** mobile application. 

---

## 📘 Overview

The dashboard provides several visualization modules designed to explore **global to local mobility patterns**:
- **Stacked Bar Charts (Altair)** — analyze mean time and distance per transport mode.
- **Podium Visualization** — ranks transport modes by usage, duration, or frequency.
- **DataFrame table** - shows mean distances per transport mode.
- **Matrix-Shaped Heatmap** — displays participant presence by town and time slot.
- **Sankey Diagram** — shows the most frequent travel flows between towns.
- **Arc Layer Map** — visualizes inter-city trips using curved arcs.
- **Detailed Heatmap** — represents intra-town movement intensity.
- **Pie Charts** — show intra-town transport mode distribution.

All modules are fully interactive, filterable, and linked through Streamlit’s reactive architecture.

---

## ⚙️ Technologies and Frameworks

The project is implemented entirely in **Python** using the following main libraries:

- [Streamlit](https://streamlit.io/) — for web app deployment and UI.
- [Pydeck](https://pydeck.gl/) — for map-based visualizations.
- [Matplotlib](https://matplotlib.org/) — for static charts.
- [Vega-Altair](https://altair-viz.github.io/) — for interactive bar and time-based visualizations.
- [GeoPy](https://geopy.readthedocs.io/) — for geocoding town coordinates.
- [Plotly](https://plotly.com/python/) — for the Sankey diagram.
- [Pickle](https://docs.python.org/3/library/pickle.html) — for serialization and caching.

---

## 🧩 Project Structure

mobility-patterns-dashboard/
│
├── data/ # (Not included) Input datasets (.csv) from the SWICE app
├── cache/ # (Not included) Pickle cache files (.pkl)
│
├── scripts/
│ ├── arcLayer.py # Inter-city mobility visualization
| ├── dataFrameMain.py # Table for distance visualization
│ ├── heatmap.py # Intra-town movement intensity visualization
│ ├── heatmapArray.py # Participant presence heatmap
│ ├── piechart.py # Transport mode distribution
│ ├── plot.py # Sankey flow diagram implementation
│ ├── podium.py # Top 3 transport modes ranking
| ├── sankey.py # Sankey flow diagram implementation
│ ├── filterToDF.py # Data filtering utilities
│ └── citiesNamesFromGeohash.py # Geocoding and town name resolution
│
├── app.py # Main Streamlit entry point
├── requirements.txt # Python dependencies
└── README.md # Project documentation

---

## 🚀 How to Run

```bash
git clone https://github.com/ClaraGaboriau/mobility-patterns-dashboard.git
cd mobility-patterns-dashboard

python -m venv venv
source venv/bin/activate       # (Linux/Mac)
venv\Scripts\activate          # (Windows)

pip install -r requirements.txt

streamlit run app.py
```

## ⚠️ Important Notes
No datasets are included in this repository for privacy and confidentiality reasons.
The dashboard requires access to the anonymized SWICE datasets (all_movements.csv, all_paths.csv) to function correctly.
Pickle cache files (.pkl) used for performance optimization (e.g., geocoding results and precomputed data) are not provided.
These files are automatically generated during runtime when the dashboard processes data for the first time.
The visualizations are designed for research and educational use, not for production deployment.
