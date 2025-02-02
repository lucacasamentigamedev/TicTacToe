#include "TicTacToe.h"

int main() {
    game_init();

    while (!quit && !WindowShouldClose()) {
        game_receive_packet();
        switch (gamestate) {
            case JOIN:
                game_join_process_input();
                game_join_draw();
                break;
            case LOBBY:
                game_lobby_process_input();
                game_lobby_draw();
                break;
            case PLAY:
                game_play_process_input();
                game_play_update();
                game_play_draw();
                break;
        }
    }

    game_deinit();
    return 0;
}
