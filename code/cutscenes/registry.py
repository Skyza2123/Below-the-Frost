from typing import Dict, Any, Optional

try:
    # use the root-level authoring file
    from data.scenes.data_cutscenes import cutscenes as CUTSCENES
except (ImportError, ModuleNotFoundError):
    CUTSCENES = {}

def get_cutscene(cutscene_id: str) -> Optional[Dict[str, Any]]:
    return CUTSCENES.get(cutscene_id)
