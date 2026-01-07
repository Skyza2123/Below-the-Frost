from data.scenes.data_cutscenes import cutscenes as CUTSCENES


def get_cutscene(cutscene_id: str):
    """Return the raw cutscene data (dict) for the given id.

    The data files use `cutscenes` lowercase; normalize the import here so
    other code can request by id.
    """
    return CUTSCENES[cutscene_id]
