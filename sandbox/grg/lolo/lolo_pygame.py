#!/usr/bin/env python


import sys
import pygame
import numpy as np

class Player():
    def __init__(self, sprite_filename):
        self.image = pygame.image.load(sprite_filename).convert_alpha()
        self.position = [1, 2]
        self.isMoving = []
        self.hasBox = False
        self.has_won = 0 # 0 : game not finished  1 : lost  2 : won

    def moveUp(self):
        self.position[1] -= 1
    def moveDown(self):
        self.position[1] += 1
    def moveRight(self):
        self.position[0] += 1
    def moveLeft(self):
        self.position[0] -= 1

    def action(self, board, tictactoe):
        if self.hasBox:
            if board[self.position[0], self.position[1]] == 8:
                self.hasBox = False
                play_tictactoe((self.position[0] - 10, self.position[1] - 10), tictactoe)
                cpu_tictactoe(tictactoe)

        else:
            if board[self.position[0], self.position[1]] == 6 \
              and self.position[0] == 17:
                self.hasBox = True
                board[self.position[0], self.position[1]] = 0


class Sprite():
    def __init__(self, sprite_filename, walkable=True):
        self.image = pygame.image.load(sprite_filename).convert_alpha()
        self.isWalkable = walkable


def on_render(screen, board, sprites, player):

    black = 0, 0, 0
    screen.fill(black)
    sprite_size = sprites[0].image.get_rect()[2:4]
    for i, row in enumerate(board):
        for j, value in enumerate(row):
            screen.blit(sprites[int(value)].image, (i*sprite_size[0], j*sprite_size[1]))
    screen.blit(player.image, [i*j for i,j in zip(player.position, sprite_size)] )
    pygame.display.flip()

def on_loop(screen, board, sprites, player):

    if len(player.isMoving) != 0:
        for move in player.isMoving:
            if move == 'down' and sprites[board[player.position[0], player.position[1] + 1]].isWalkable:
                player.moveDown()
            elif move == 'up' and sprites[board[player.position[0], player.position[1] - 1]].isWalkable:
                player.moveUp()
            elif move == 'left' and sprites[board[player.position[0] - 1, player.position[1]]].isWalkable:
                player.moveLeft()
            elif move == 'right' and sprites[board[player.position[0] + 1, player.position[1]]].isWalkable:
                player.moveRight()
            pygame.time.delay(100)

    if player.has_won != 0:
        board[17,9:14] = 0
    if player.has_won == 2:
        board[17,1] = 0

def play_tictactoe(position, tictactoe):
    tictactoe[position[0], position[1]] = 2

def cpu_tictactoe(tictactoe):
    import random
    box = random.randint(0,8)
    while tictactoe.item(box) != 0:
        box = random.randint(0,8)

    tictactoe.put(box, 1)


def has_won(tictactoe):
    if np.all(tictactoe[0,:] == 1) or np.all(tictactoe[1,:] == 1) or np.all(tictactoe[2,:] == 1):
        return 1
    elif np.all(tictactoe[0,:] == 2) or np.all(tictactoe[1,:] == 2) or np.all(tictactoe[2,:] == 2):
        return 2
    elif np.all(tictactoe[:,0] == 1) or np.all(tictactoe[:,1] == 1) or np.all(tictactoe[:,2] == 1):
        return 1
    elif np.all(tictactoe[:,0] == 2) or np.all(tictactoe[:,1] == 2) or np.all(tictactoe[:,2] == 2):
        return 2
    elif tictactoe[0,0] == tictactoe[1,1] and tictactoe[1,1] == tictactoe[2,2]:
        return tictactoe[1,1]
    elif tictactoe[0,-1] == tictactoe[1,1] and tictactoe[1,1] == tictactoe[-1,0]:
        return tictactoe[1,1]
    return 0

def update_board(board, tictactoe):
    tic = tictactoe.copy()
    tic[tic==0] = 8
    tic[tic==1] = 7
    tic[tic==2] = 6
    board[10:13,10:13] = tic

def __main__():

    pygame.mixer.init()
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.init()

    #create the music
    pygame.mixer.music.load('lolo.ogg')
    pygame.mixer.music.play()

    #create the screen
    screen_size = 640, 480
    screen = pygame.display.set_mode(screen_size)

    #create the game board
    board_size = 25, 19
    board = np.zeros(board_size, dtype=np.int16)
    board[0,:]=1
    board[20,:]=1
    board[21,:]=1
    board[:,0]=1
    board[:,1]=1
    board[1:20,1]=5
    board[:,15]=1
    board[5,13]=2
    board[6,12]=3
    board[17,1]=4

    board[10:13,10:13]=8
    board[17,9:14]=6

    #create the game
    tictactoe = np.zeros((3,3), dtype=np.int16)

    #create the sprites
    sprites = []
    sprites.append( Sprite('background.jpg', True) )
    sprites.append( Sprite('wall.jpg', False) )
    sprites.append( Sprite('stone.png', False) )
    sprites.append( Sprite('tree.png', False) )
    sprites.append( Sprite('door.png', False) )
    sprites.append( Sprite('frontwall.png', False) )
    sprites.append( Sprite('heart.png', True) )
    sprites.append( Sprite('box.png', True) )
    sprites.append( Sprite('black.png', True) )

    #create the player
    player = Player('player.png')

    while not player.position == [17,1]:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    player.isMoving.append('up')
                elif event.key == pygame.K_DOWN:
                    player.isMoving.append('down')
                elif event.key == pygame.K_LEFT:
                    player.isMoving.append('left')
                elif event.key == pygame.K_RIGHT:
                    player.isMoving.append('right')
                elif event.key == pygame.K_ESCAPE:
                    sys.exit(0)
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_UP:
                    player.isMoving.pop(player.isMoving.index('up'))
                elif event.key == pygame.K_DOWN:
                    player.isMoving.pop(player.isMoving.index('down'))
                elif event.key == pygame.K_LEFT:
                    player.isMoving.pop(player.isMoving.index('left'))
                elif event.key == pygame.K_RIGHT:
                    player.isMoving.pop(player.isMoving.index('right'))
                elif event.key == pygame.K_SPACE:
                    player.action(board, tictactoe)
                    update_board(board, tictactoe)
                    player.has_won = has_won(tictactoe)
            else:
                pass #print event
        on_loop(screen, board, sprites, player)
        on_render(screen, board, sprites, player)
    pygame.quit()


if __name__ == '__main__':

    __main__()
