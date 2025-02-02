#include "TicTacToe.h"
#include "client.h"
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

int grid[GRID_SIZE * GRID_SIZE] = {0};
Game_State gamestate = JOIN;
const int screen_width = GRID_SIZE*CELL_SIZE;
const int screen_height = GRID_SIZE*CELL_SIZE;
int quit=0;
char player_name[20] = {0};
uint32_t rooms_ids[10] = {0};
int name_index=0;
char room_id_text[10] = ""; 
int room_index = 0;

void game_init()
{
    InitWindow(screen_width, screen_height, "Tic Tac Toe");
    SetTargetFPS(60);
    if (initialize_socket(SERVER_IP, SERVER_PORT) < 0)
    {
        quit=1;
    }
}

void game_receive_packet()
{
    char buffer[64]={0};
    int bytes_received = receive_packet(buffer, sizeof(buffer));
    if(bytes_received >= 4)
    {
        uint32_t command;
        memcpy(&command, buffer, sizeof(command));
        switch (command)
        {
        case COMMAND_SEND_GAME_STATE:
            if (bytes_received == 8)
            {
                uint32_t new_state;
                memcpy(&new_state, buffer + sizeof(command), sizeof(new_state));
                gamestate=new_state;
            }
            break;
        case COMMAND_UPDATE_ROOM:
            if (bytes_received == 44)
            {
                memcpy(rooms_ids, buffer + sizeof(command), sizeof(rooms_ids));
            }
            break;
        case COMMAND_SEND_PLAYFIELD :
            if(bytes_received == 40)
            {
                memcpy(grid, buffer + sizeof(command), sizeof(grid));
            }
        break;
        default:
            printf("Unknown command received: %u\n", command);
            break;
        }
    }
}

void game_join_process_input()
{
    int key= GetCharPressed();
    if(key >= 32 && key <= 126 && name_index < 19)
    {
        player_name[name_index] = (char)key;
        name_index++;
        player_name[name_index] = '\0';
    }
    if (IsKeyPressed(KEY_BACKSPACE) && name_index > 0) 
    {
        name_index--;
        player_name[name_index] = '\0';
    }
    if (IsKeyPressed(KEY_ENTER) && name_index > 0) 
    {
        join();
    }
}

void game_join_draw()
{
    BeginDrawing();
    ClearBackground(RAYWHITE);

    DrawText("Enter player name (19 characters max):", 10, 50, 20, DARKGRAY);
    DrawText(player_name, 50, 90, 20, DARKGRAY);

    EndDrawing();
}

void join()
{
    char buffer[24]={0}; 
    uint32_t command = COMMAND_JOIN;
    memcpy(buffer, &command, sizeof(command));
    memcpy(buffer + sizeof(command), player_name, sizeof(player_name)); 
    send_packet(buffer, sizeof(buffer));
}

void game_lobby_process_input()
{
    if (IsKeyPressed(KEY_SPACE)) 
    {
        uint32_t command = COMMAND_CREATE_ROOM;
        send_packet((char*)&command, sizeof(command));
    }

    int key = GetCharPressed();
    if (key >= '0' && key <= '9' && room_index < sizeof(room_id_text) - 1) 
    {
        room_id_text[room_index] = (char)key;
        room_index++;
        room_id_text[room_index] = '\0';
    }
    if (IsKeyPressed(KEY_BACKSPACE) && room_index > 0) 
    {
        room_index--;
        room_id_text[room_index] = '\0';
    }

    if (IsKeyPressed(KEY_ENTER) && room_index > 0) 
    {
        int room_id = atoi(room_id_text); // Converti in int
        uint32_t packet[2] = {COMMAND_CHALLENGE, (uint32_t)room_id};
        send_packet((char*)packet, sizeof(packet));

        printf("Sfida inviata alla stanza %d\n", room_id);
    }
}

void game_lobby_draw()
{
    BeginDrawing();
    ClearBackground(BLUE);
    DrawText("Premi SPAZIO per creare una stanza", 10, 50, 20, WHITE);
    DrawText("Stanze disponibili:", 10, 90, 20, WHITE);

    int y_offset = 120;

    for (int i = 0; i < 10; i++) 
    {
        if (rooms_ids[i] != 0)
        {
            char room_text[50];
            sprintf(room_text, "Stanza ID: %d", rooms_ids[i]);
            DrawText(room_text, 10, y_offset, 20, WHITE);
            y_offset += 30;
        }
    }
    DrawText("Inserisci ID stanza per sfidare:", 10, y_offset + 20, 20, WHITE);
    DrawText(room_id_text, 10, y_offset + 50, 20, YELLOW);
    EndDrawing();
}

void game_play_process_input()
{
    if (IsMouseButtonPressed(MOUSE_LEFT_BUTTON)) {
        Vector2 mousePos = GetMousePosition();
        uint32_t cellWidth = screen_width / GRID_SIZE; 
        uint32_t cellHeight = screen_height / GRID_SIZE;
        uint32_t col = mousePos.x / cellWidth;
        uint32_t row = mousePos.y / cellHeight;
        uint32_t index = row * GRID_SIZE + col;
        uint32_t packet[2] = {COMMAND_MOVE, index};
        send_packet((char*)packet, sizeof(packet));
        printf("Hai cliccato sulla cella: %d\n", index);
    }
}
void game_play_update()
{

}

void DrawGridButtons(int screenWidth, int screenHeight, int grid[9]) 
{
    int cellWidth = screenWidth / GRID_SIZE;
    int cellHeight = screenHeight / GRID_SIZE;

    for (int row = 0; row < GRID_SIZE; row++) {
        for (int col = 0; col < GRID_SIZE; col++) {
            int x = col * cellWidth;
            int y = row * cellHeight;
            int index = row * GRID_SIZE + col;
            Rectangle button = { x, y, cellWidth, cellHeight };
            Color color = LIGHTGRAY;
            DrawRectangleRec(button, color);
            DrawRectangleLinesEx(button, 2, BLACK);
            if (grid[index] == 1) {
                DrawLine(x + 20, y + 20, x + cellWidth - 20, y + cellHeight - 20, BLACK);
                DrawLine(x + 20, y + cellHeight - 20, x + cellWidth - 20, y + 20, BLACK);
            } else if (grid[index] == 2) {
                DrawCircleLines(x + cellWidth / 2, y + cellHeight / 2, cellWidth / 3, BLACK);
            }
        }
    }
}
void game_play_draw()
{
    BeginDrawing();
    DrawGridButtons(screen_width, screen_height, grid);
    EndDrawing();
}


void game_deinit()
{
    uint32_t command = COMMAND_QUIT;
    send_packet((char*)&command, sizeof(command));
    deinit_client();
}