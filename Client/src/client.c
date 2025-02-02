#include "client.h"

#ifdef _WIN32
#include <WinSock2.h>
#include <ws2tcpip.h>
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#endif

#include <stdio.h>
#include <stdint.h>

int s = -1;
struct sockaddr_in send_sin;

int initialize_socket(const char *server_ip, int server_port)
{
    #ifdef _WIN32
        // this part is only required on Windows: it initializes the Winsock2 dll
        WSADATA wsa_data;
        if (WSAStartup(0x0202, &wsa_data))
        {
            printf("unable to initialize winsock2 \n");
            return -1;
        }
    #endif
    s = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (s < 0)
    {
        printf("unable to initialize the UDP socket \n");
        return -1;
    }
    printf("socket %d created\n", s);

    memset(&send_sin, 0, sizeof(send_sin));

    send_sin.sin_family = AF_INET;
    send_sin.sin_port = htons(server_port); // converts 9999 to big endian
    if(inet_pton(AF_INET, server_ip, &send_sin.sin_addr) <= 0)
    {
        printf("Error: invalid IP address '%s'\n ", server_ip);
        return -1;
    }

    #ifdef _WIN32
        unsigned long nb_mode = 1;
        if (ioctlsocket(s, FIONBIO, &nb_mode) !=0)
        {
            printf("Error: failed to set non-blocking mode\n");
            return -1;
        }
    #else
        int flags = fcntl(s, F_GETFL, 0);
        if (flags < 0)
        {
            printf("Error: fcntl(F_GETFL) failed\n");
            return -1;
        }
        if (fcntl(s, F_SETFL, flags | O_NONBLOCK) < 0)
        {
            printf("Error: fcntl(F_SETFL) failed\n");
            return -1;
        }
    #endif
    return 0; 
}

void send_packet(const char *buffer, size_t length)
{
    if (buffer == NULL || length == 0)
    {
        printf("Error: invalid buffer or length\n");
        return;
    }

    if (s < 0)
    {
        printf("Error: socket is not initialized\n");
        return;
    }

    int bytes_sent = sendto(s, buffer, length, 0, (struct sockaddr*)&send_sin, sizeof(send_sin));

    if (bytes_sent < 0)
    {
        printf("Error sending packet");
    }
    printf("Packet send\n");
}

int receive_packet(char *buffer, size_t buffer_size) 
{
    struct sockaddr_in rcv_sin;
    socklen_t rcv_sin_len = sizeof(rcv_sin);
    
    int bytes_received = recvfrom(s, buffer, buffer_size, 0, (struct sockaddr*)&rcv_sin, &rcv_sin_len);
    
    if (bytes_received < 0) 
    {
        return -1;
    }

    printf("Received %d bytes\n", bytes_received);
    return bytes_received;
}



void deinit_client()
{
    if (s >= 0)
    {
        #ifdef _WIN32
            closesocket(s);
        #else
            close(s);
        #endif
        s = -1;
    }

    #ifdef _WIN32
        WSACleanup();
    #endif
}