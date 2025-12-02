# HEP_Calorimeter_DNN

This repository contains a small simulation and machine-learning project exploring energy deposition and regression performance for simplified electromagnetic (ECAL) and hadronic (HCAL) calorimeter designs. The work was carried out using a custom lightweight Geant4-style geometry description and event simulation framework, followed by several deep-neural-network models for energy regression.

The goal is to compare different calorimeter configurations, study energy-confinement behavior, generate training datasets, and evaluate the performance of multiple DNN architectures under varying detector geometries and particle types.

---

## Overview of the Workflow

The project consists of three main stages:

### **1. Detector Geometry & Particle Simulation**
The detector is defined using:

- `Design.py` — parametric ECAL/HCAL geometry definition  
- `G4Calo.py` — simple Geant4-style calorimeter simulation  
- `Simulations.py` / `Trackers.py` — event steering, utilities  
- `PbWO4_props.ipynb` — material and optical properties exploration  

Energy deposition studies are performed in:

- **`EnergyDeposition.ipynb`**  
  Visualizes deposited energy per layer and examines energy confinement for different ECAL/HCAL configurations.

Based on these studies, suitable detector geometries are selected.

---

### **2. Dataset Generation**
After identifying promising designs, synthetic datasets are produced in:

- **`DataGenerator.ipynb`**

This notebook generates per-event summaries (e.g., energy per layer, particle type, initial energy), which are then used as input features for the regression networks.

---

### **3. Deep Neural Network Models**
Three neural-network approaches were explored:

1. **`Initial_Train_Eval.ipynb`**  
   The main and best-optimized DNN.  
   Performs training, validation, and energy regression with improved preprocessing and hyperparameter tuning.

2. **`ScndEHCAL.ipynb`**  
   An alternative model focusing on different feature combinations and ECAL/HCAL treatment.

3. **`SeparateParticles.ipynb`**  
   Trains and evaluates separate networks for photons and charged pions  
   (to study whether particle-specific training improves regression accuracy).

W&B experiment tracking was used to monitor and compare the training behavior of different networks.

---

## Methods

### **Simulation**
- Custom Geant4-style calorimeter model  
- Parametric ECAL/HCAL geometry description  
- Study of PbWO₄ properties (density, attenuation, X₀, etc.)  
- Particle transport and energy deposition sampling  

### **Machine Learning**
- Fully-connected regression models built in PyTorch  
- Standardization and preprocessing  
- Training/validation splits  
- Particle-specific vs mixed-particle training  
- Performance comparison between calorimeter designs  

### **Experiment Tracking (Weights & Biases)**
Training runs were logged using the Weights & Biases (wandb) platform, including:

- loss curves  
- hyperparameters  
- regression metrics  
- comparisons across detector geometries and architectures  

W&B was used to track convergence, detect overfitting, and evaluate alternative designs systematically.

---


## Notes

- This project focuses on conceptual exploration, not on full detector realism.  
- The notebooks reflect different stages of model and simulation development.  
- The results demonstrate how calorimeter design choices affect regression performance in simplified setups.  

---

## Contact

**Ege Eroğlu**  
Karlsruhe Institute of Technology  
egeeroglu@gmail.com

