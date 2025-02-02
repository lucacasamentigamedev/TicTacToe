#ifndef CLIENT_H
#define CLIENT_H

int initialize_socket(const char *server_ip, int server_port);
void send_packet(const char *buffer, size_t length);
int receive_packet(char *buffer, size_t buffer_size);
void deinit_client();

#endif