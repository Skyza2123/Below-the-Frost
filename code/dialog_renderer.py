from settings import WINDOW_WIDTH, WINDOW_HEIGHT, COLORS


def draw_dialog(game, surface):
    """Draw the active dialog panel and text for the game onto the provided surface.
    This mirrors the dialog drawing that used to be inside Game.run().
    """
    if game.dialog_tree and not game.ui_manager.modal_open:
        panel = game.ui_assets.dialog_panel  # provided by UIAssets
        x = (WINDOW_WIDTH - panel.get_width()) // 2
        y = WINDOW_HEIGHT - panel.get_height() - 12
        surface.blit(panel, (x, y))

        line = game.dialog_tree.dialog[game.dialog_tree.dialog_index]
        text = game.font["dialog"].render(line, False, COLORS["pure white"])
        surface.blit(text, (x + 30, y + 22))
