#ifndef TICTACTOE_H
#define TICTACTOE_H

#include "raylib.h"

#define GRID_SIZE 3
#define CELL_SIZE 150
#define SERVER_PORT 9999
#define SERVER_IP "127.0.0.1"
#define COMMAND_JOIN 0
#define COMMAND_CREATE_ROOM 1
#define COMMAND_CHALLENGE 2
#define COMMAND_MOVE 3
#define COMMAND_QUIT 4

#define COMMAND_UPDATE_ROOM  5
#define COMMAND_SEND_PLAYFIELD 6
#define COMMAND_SEND_GAME_STATE 7


typedef enum {JOIN, LOBBY, PLAY } Game_State;

extern Game_State gamestate;
extern int quit;


void game_init();
void game_receive_packet();

void game_join_process_input();
void game_join_draw();
void join();

void game_lobby_process_input();
void game_lobby_draw();

void game_play_process_input();
void game_play_update();
void game_play_draw();


void game_deinit();

#endif