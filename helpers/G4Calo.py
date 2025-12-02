
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Layer:
    thickness_cm: float
    material: str
    sensitive: bool = False

@dataclass
class GeometryDescriptor:
    area_m2: float = 1.0
    layers: List[Layer] = field(default_factory=list)

    # Design.py expects exactly this:
    def addLayer(self, thickness_cm: float, material: str, sensitive: bool=False):
        self.layers.append(Layer(float(thickness_cm), str(material), bool(sensitive)))

    # handy if Design ever calls this:
    def as_specs(self) -> Dict[str, Any]:
        return {
            "total_len_cm": float(sum(L.thickness_cm for L in self.layers)),
            "total_lambda": None,
            "layers": [{"material": L.material, "thickness_cm": L.thickness_cm, "sensitive": L.sensitive} for L in self.layers],
        }
