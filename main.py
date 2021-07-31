import pygame, sys, math, random, time, copy, itertools, threading, os

# Thanks to nilaym on gitHub for their Bejewled code!
# pygame General setup
pygame.init()
clock = pygame.time.Clock()

# Setting up pygame's window
screen_width = int(1920/2)
screen_height = int(1080/2)
screen = pygame.display.set_mode((screen_width,screen_height))
pygame.display.set_caption('Puzzle')

# Key bindings
button0 = pygame.K_a
button1 = pygame.K_s
button2 = pygame.K_d
upArrow = pygame.K_UP
downArrow = pygame.K_DOWN
leftArrow = pygame.K_LEFT
rightArrow = pygame.K_RIGHT

# Images
gameBG = pygame.image.load(os.path.join('sprites', 'spr_bg.png')).convert()
cursor = pygame.image.load(os.path.join('sprites', 'spr_cursor.png')).convert_alpha()

# Game variables
gridSize = 40
animSpd = 20

# Block n' Board control
EMPTY = -1
blockNum = 4
blockSize = 40
charSize = 140
# Power damage
threeMatch = 40
fourMatch = 70
fiveMatch = 150
# Remember to double these sizes when you get to Renpy thanks
BOARDWIDTH = 240
BOARDHEIGHT = 480
boardXmin = 194
boardXmax = 354.5
boardYmin = 35
boardYmax = 475.5

ROWS = 12
COLUMNS = 6

# Make sure the board stays even
assert (BOARDWIDTH * BOARDHEIGHT) % 2 == 0, 'Need even board!'
# Have an image for the board. lol
board = pygame.image.load(os.path.join('sprites', 'spr_window.png')).convert()
boardPos = (194,35) # Remember to double this

def Text(font, size, text, color, x, y):
    fonts = pygame.font.Font(os.path.join('fonts', 'fnt_' + font + '.ttf'), size)
    string = fonts.render(text, True, color)
    screen.blit(string,(x,y))

class Cursor(object):
    def __init__(self):
        self.x = boardXmin
        self.y = boardYmin
        self.keyDirection = pygame.math.Vector2(0,0)
        self.image = cursor
        self.canControl = True
        # Rect for blit position
        self.rect = self.image.get_rect()
        # Hitbox 1
        self.hitA = (self.x, self.y, blockSize, blockSize)
        # Hitbox 2
        self.hitB = (self.x + blockSize, self.y, blockSize, blockSize)
    def draw(self, surface):
        surface.blit(cursor, (self.x, self.y))
        self.hitA = (self.x, self.y, blockSize, blockSize)
        self.hitB = (self.x + blockSize, self.y, blockSize, blockSize)
        # Keep cursor movement within the grid
        # self.x += (round(float(self.keyDirection.x)/gridSize))*gridSize # This worked with Python 2, but it won't work properly on 3 me angy
        # self.y += (round(float(self.keyDirection.y)/gridSize))*gridSize
        self.x = self.keyDirection.x
        self.y = self.keyDirection.y
        # Limit cursor to only be within board
        if self.x <= boardXmin:
            self.x = boardXmin
        elif self.x >= boardXmax:
            self.x = boardXmax
        if self.y <= boardYmin:
            self.y = boardYmin
        elif self.y >= boardYmax:
            self.y = boardYmax
# Game control
class GameBoard:
    def __init__(self, blockFall, player, enemy, playerHP, enemyHP, blockColors, enemyTurns, minAtk, maxAtk):
        self.screen = pygame.display.get_surface()
        self.rows = ROWS
        self.columns = COLUMNS
        # Set up the board's 2D Array
        self.board =  []
        for r in range(self.rows):
            self.board.append([])
        for row in self.board:
            for c in range(self.columns):
                row.append(None)
        # 2D Array of the board, used for match detection
        self.boardTable = [
            [-1, -1, -1, -1, -1],
            [-1, -1, -1, -1, -1],
            [-1, -1, -1, -1, -1],
            [-1, -1, -1, -1, -1],
            [-1, -1, -1, -1, -1],
            [-1, -1, -1, -1, -1],
            [-1, -1, -1, -1, -1]
        ]
        self.blockColors = blockColors
        if self.blockColors <= 1:
            # Board needs at least 3 different colors
            self.blockColors = 2
        if self.blockColors > blockNum:
            # If the number given in blockColors is more than blockNum then default to max colors
            self.blockColors = blockNum

        self.countTime = pygame.time.get_ticks()
        self.waitTimeStatic = blockFall
        self.waitTime = blockFall
        self.pick1, self.pick2 = None, None
        self.dropBlocks = []
        self.canAdd = True
        self.allClear = False
        # Characters
        self.player = Character(self, player, 0, 0, playerHP)
        self.enemy = Character(self, enemy, 0, 0, enemyHP)
        self.minEnemyAtk = minAtk
        self.maxEnemyAtk = maxAtk
        self.maxEnemyTurn = enemyTurns # Now with new turn-based flavor!
        self.enemyTurn = self.maxEnemyTurn


        # Rects to represent where a block would be
        self.boardRects = []
        for r in range(self.rows):
            self.boardRects.append([])
        self.setBoard()
        self.animProgress = 0
        self.state = 'start'
    def setBoard(self):
        # Set up reference board rects
        x,y = boardXmin,(boardYmin-5)
        for row in self.boardRects:
            for c in range(self.columns):
                rect = pygame.Rect(x,y,blockSize,blockSize)
                row.append(rect)
                x += blockSize
            x = boardXmin
            y += boardYmin + 5

        # Add blocks to each empty space in the array
        for r in range(self.rows):
            if r == ROWS-1:
                for c in range(self.columns):
                    image = random.randint(0, self.blockColors)
                    x,y = self.boardRects[r][c].left, self.boardRects[r][c].bottom - boardYmin
                    block = Block(image, (x,y))
                    self.board[r][c] = block
            elif r <= ROWS-1:
                for c in range(self.columns):
                    image = EMPTY
                    x,y = self.boardRects[r][c].left, self.boardRects[r][c].bottom - boardYmin
                    block = Block(image, (x,y))
                    self.board[r][c] = block


        # Don't start with matches!
        # Horizontal check
        for row, column in itertools.product(range(self.rows), range(self.columns-2)):
            if self.board[row][column].index is not EMPTY and self.board[row][column].index == self.board[row][column+1].index == self.board[row][column+2].index: #A match!
                # Change the image index of the first block
                top, bottom, left, right = EMPTY, EMPTY, EMPTY, EMPTY
                if row+1 < self.rows:
                    bottom = self.board[row+1][column].index
                if row-1 > 0:
                    top = self.board[row-1][column].index
                if column+1 < self.columns:
                    right = self.board[row][column+1].index
                if column-1 > 0:
                    left = self.board[row][column-1].index

                surroundingBlocks = [top, bottom, left, right]

                blockTypes = [] # List of block types from 0 to blockColors

                for x in range(self.blockColors+1):
                    blockTypes.append(x)

                for b in surroundingBlocks:
                    if b in blockTypes:
                        blockTypes.remove(b)

                self.board[row][column].index = random.choice(blockTypes) # Pick a new block

        # Vertical check
        for row, column in itertools.product(range(self.rows-2), range(self.columns)):
            if self.board[row][column].index is not EMPTY and self.board[row][column].index == self.board[row+1][column].index == self.board[row+2][column].index:
                top, bottom, left, right = EMPTY, EMPTY, EMPTY, EMPTY
                if row+1 < self.rows:
                    bottom = self.board[row+1][column].index
                if row-1 > 0:
                    top = self.board[row-1][column].index
                if column+1 < self.columns:
                    right = self.board[row][column+1].index
                if column-1 > 0 and self.board[row][column-1] is not None:
                    left = self.board[row][column-1].index

                surroundingBlocks = [top, bottom, left, right]

                blockTypes = []
                for x in range(self.blockColors+1):
                    blockTypes.append(x)

                for b in surroundingBlocks:
                    if b in blockTypes:
                        blockTypes.remove(b)

                self.board[row][column].index = random.choice(blockTypes)

    def refreshBoard(self):
        self.state = 'removeMatches' # For when a new row of blocks is being generated
        # Reset the board based on the board copy
        for row in range(self.rows):
            for column in range(self.columns):
                if self.board[row][column] is not None:
                    self.board[row][column].rect.bottomleft = self.boardRects[row][column].bottomleft
                    self.board[row][column].rect.move_ip(0,5) # Without this the board moves up 5 pixels
        # Make a table of the board's block's indexes
        newBoard = []
        for row in range(self.rows):
            columns = []
            for column in range(self.columns):
                columns.append(self.board[row][column].index)

            newBoard.append(columns)
        self.boardTable = newBoard

        if all(index == -1 for index in itertools.chain(*self.boardTable)) == True:
            self.allClear = True

    def generateBlocks(self):
        newBlocks = []
        newRow = 1
        for r in range(newRow):
            newBlocks.append([])
        for row in newBlocks:
            for c in range(self.columns):
                row.append(None)

        x,y = boardXmin,(boardYmin-5)
        #self.canAdd = True

        #Make new row of blocks to generate at the bottom of board
        for r in range(newRow):
            for c in range(self.columns):
                image = random.randint(0, self.blockColors)
                x,y = self.boardRects[r][c].left, self.boardRects[r][c].bottom - boardYmin
                block = Block(image, (x,y))
                newBlocks[r][c] = block

        # Horizontal check
        for row, column in itertools.product(range(newRow), range(self.columns-2)):
            if newBlocks[row][column].index == newBlocks[row][column+1].index == newBlocks[row][column+2].index: #A match!
                        # Change the image index of the first block
                top, bottom, left, right = EMPTY, EMPTY, EMPTY, EMPTY
                if row+1 < newRow:
                    bottom = newBlocks[row+1][column].index
                if row-1 > 0:
                    top = newBlocks[row-1][column].index
                if column+1 < self.columns:
                    right = newBlocks[row][column+1].index
                if column-1 > 0:
                    left = newBlocks[row][column-1].index

                surroundingBlocks = [top, bottom, left, right]

                blockTypes = [] # List of block types from 0 to blockColors

                for x in range(self.blockColors+1):
                    blockTypes.append(x)

                for b in surroundingBlocks:
                    if b in blockTypes:
                        blockTypes.remove(b)

                newBlocks[row][column].index = random.choice(blockTypes) # Pick a new block

        # Check if  there's a block on the top of the board
        rowCheck = self.boardTable[0]
        if all(x == rowCheck[0] for x in rowCheck) == True:
            self.canAdd = True # If all the numbers in rowCheck are the same, then a new row can be added
        elif all(x == rowCheck[0] for x in rowCheck) == False:
            self.canAdd = False # If all the numbers in rowCheck aren't the same, then a new row can't be added
        if self.player.health == 0 or self.enemy.health == 0:
            self.canAdd = False
        if self.state == 'removeMatches' or self.state == 'dropping':
            self.canAdd = False
        if self.canAdd == True:
            for block in newBlocks:
                self.board.pop(0) # Get rid of the topmost row
                self.board.append(block) # Add the new blocks
                self.refreshBoard()

    def runGenerate(self):
        # For when the board has to wait to generate a new row of blocks
        now = pygame.time.get_ticks()
        if now - self.countTime >= self.waitTime:
            self.countTime = now
            self.waitTime = self.waitTimeStatic
            self.generateBlocks()

    def getBoard(self):
        # This was in the Bejewled code, I don't use this for anything. Could this be removed?
        """ Returns board structure as a generator """
        for row in self.board:
            yield row

    def draw(self):
        for row in self.board:
            for block in row:
                if block is not None:
                    block.draw()
        self.player.blitme(450, 120)
        self.enemy.blitme(650, 120)

    def checkButtonPress(self,hitbox):
        # For cursor control
        for row in self.board:
            for block in row:
                if block is not None and block.rect.collidepoint(hitbox):
                    r = self.board.index(row)
                    b = row.index(block)
                    return (r,b)

        return (0,0) # Temporary fix lol
    def swapBlocks(self, pos1, pos2):
        row1, column1 = pos1
        row2, column2 = pos2
        # Swap the blocks
        if pos1 is None and pos2 is None:
            pass
        else:
            self.board[row1][column1].index, self.board[row2][column2].index = self.board[row2][column2].index, self.board[row1][column1].index
        # Check if a block and empty spot were swapped, if they were then start the drop
        if self.board[row1][column1].index == EMPTY or self.board[row2][column2].index == EMPTY:
            self.getDropBlocks()
            self.state = 'dropping'


    def checkForMatches(self):
        # Thanks to NovaSquirrel for the code
        height = len(self.boardTable)
        width = len(self.boardTable[0])
        match = set()

        for row in range(height):
            for column in range(width):
                color = self.boardTable[row][column]
                if color != -1:
                    if column != 0 and column != width-1:
                        if self.boardTable[row][column-1] == color and self.boardTable[row][column+1] == color:
                            match.add((row, column-1))
                            match.add((row, column))
                            match.add((row, column+1))
                    if row != 0 and row != height-1:
                        if self.boardTable[row-1][column] == color and self.boardTable[row+1][column] == color:
                            match.add((row-1, column))
                            match.add((row, column))
                            match.add((row+1, column))

        return match

    def removeMatches(self):
        matches = self.checkForMatches()

        threes = 0
        fours = 0
        fives = 0

        for match in matches:
            if len(matches) == 3:
                threes += 1
            elif len(matches) == 4:
                fours += 1
            elif len(matches) == 5:
                fives += 1
            elif len(matches) > 5:
                if self.player.spclMeter < self.player.maxSpclMeter:
                    self.player.spclMeter += 1
            row, column = match
            removeTimer = threading.Thread(target=self.animateBlock, args=(row, column))
            removeTimer.start()

        if len(matches) > 0:
            return threes, fours, fives # There were matches

        return 0 # No matches

    def animateBlock(self, row, column):
        # Change the matched block to its popped frame
        self.board[row][column].frame = 1
        time.sleep(0.3)
        self.board[row][column].frame = 0
        self.board[row][column].index = EMPTY

    def animatePullDown(self, dropBlocks):
        # Bring a floating block one cell down until it's not under an empty space
        anim = []
        for dropBlock in dropBlocks:
            row, column = dropBlock
            for r in range(row, -1, -1):
                if self.board[r][column].index != EMPTY:
                    if self.board[r][column].rect.bottom != self.board[row][column].rect.bottom:
                        anim.append(self.board[r][column])

        if self.animProgress < blockSize:
            for cell in anim:
                cell.rect.move_ip(0, +animSpd)
            self.animProgress += animSpd
        else:
            self.refreshBoard() # Won't animate right without this

            # Actually pull down the blocks 1 row, by setting every space's image to the image of the space above it
            for dropBlock in dropBlocks:
                row, column = dropBlock
                for r in range(row, -1, -1):
                    if r == 0:
                        self.board[r][column].index = -1

                    else:
                        self.board[r][column].index = self.board[r-1][column].index

            self.animProgress = 0 # Reset animation progress meter

            return 1
    def getDropBlocks(self):
        dropBlocks = []

        for r in range(self.rows):
            for c in range(self.columns):
                if self.board[r][c] is not None and self.board[r][c].index == EMPTY and self.board[r-1][c] is not None and self.board[r-1][c].index != EMPTY:
                    if r-1 >= 0: # Without this it will detect the blank spot on the top of the board
                        dropBlocks.append((r,c))
        return dropBlocks

    def playerInput(self):
        dt = clock.tick(20)
        if self.player.health <= 0 or self.enemy.health <= 0:
            CURSOR.canControl = False
        keys = pygame.key.get_pressed()
        if keys[upArrow]:
            CURSOR.keyDirection.y -= gridSize
        if keys[downArrow]:
            CURSOR.keyDirection.y += gridSize
        if keys[leftArrow]:
            CURSOR.keyDirection.x -= gridSize
        if keys[rightArrow]:
            CURSOR.keyDirection.x += gridSize
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == button0:
                    if self.state == 'start' or self.state == 'dropping':
                        if CURSOR.canControl is True:
                            self.pick1 = self.checkButtonPress(CURSOR.hitA[0:2])
                            self.pick2 = self.checkButtonPress(CURSOR.hitB[0:2])
                            self.swapBlocks(self.pick1, self.pick2)
                elif event.key == button1:
                    self.waitTime = 0
                elif event.key == button2:
                    if self.player.spclMeter == self.player.maxSpclMeter:
                        self.player.currentAnim = self.player.animStates['spcl']
                        self.enemy.enemyDamageCalc(400)
                        self.player.spclMeter = 0
                elif event.key == pygame.K_w:
                    #Testing.....
                    print(self.allClear)

    def boardControl(self):
        self.runGenerate()
        if self.allClear == True:
            seconds = (pygame.time.get_ticks()-self.countTime)/1000
            Text('slkscr', 20, 'All Clear!', (255,255,255), (260), (220)) # Temporary hardcoded x,y values
            if seconds >= 12:
                self.enemy.enemyDamageCalc(1500)
                self.allClear = False
        if self.state == 'start':
            # If blocks were swapped, change state to swapping
            if self.pick1 is not None and self.pick2 is not None:
                self.state = 'swapping'
        elif self.state == 'swapping':
            self.refreshBoard()
            self.pick1, self.pick2 = None, None
            if self.enemyTurn <= self.maxEnemyTurn:
                if self.enemyTurn >= 0.9 and self.enemy.health >= 0.9:
                    self.enemyTurn -= 1
            self.state = 'removeMatches'
        elif self.state == 'removeMatches':
            self.refreshBoard()
            removed = self.removeMatches() # Matches found and removed

            if removed != 0:
                dropBlocks = self.getDropBlocks()
                # Change the player's animation to their attacking one
                if self.enemy.health >= 0.9 or self.player.health >= 0.9:
                    # Don't change the animation if the enemy/player is dead
                    self.player.currentAnim = self.player.animStates['atk']
                # Damage the enemy
                for index in range(len(removed)):
                    totalDamage = 0.0
                    if removed[index] > 0:
                        if index == 0:
                            totalDamage += removed[index] * threeMatch
                        elif index == 1:
                            totalDamage += removed[index] * fourMatch
                        elif index == 2:
                            totalDamage += removed[index] * fiveMatch
                        self.enemy.enemyDamageCalc(totalDamage)
                        if self.enemyTurn <= self.maxEnemyTurn:
                            if self.enemyTurn >= 0.9  and self.enemy.health >= 0.9:
                                self.enemyTurn -= 1

                self.state = 'dropping'
            elif removed == 0: # No more matches
                if self.enemyTurn == 0:
                    self.enemy.isAtk = True
                    self.enemy.enemyAtk()
                self.refreshBoard()
                self.state = 'start'
        elif self.state == 'dropping':
            if self.animatePullDown(self.dropBlocks) == 1:
                self.dropBlocks = self.getDropBlocks()
                if self.dropBlocks != []:
                    self.refreshBoard()
                    self.state = 'dropping'
                else:
                    self.state = 'removeMatches'

    def runGame(self):
        # Visuals
        screen.blit(gameBG, gameBG.get_rect())
        screen.blit(board, boardPos)
        self.draw()
        CURSOR.draw(screen)
        # Handling input
        self.playerInput()
        # Board control, board control
        self.boardControl()
        # Updating the window
        pygame.display.flip()
        clock.tick(60) # Limit FPS

class Block:
    def __init__(self,image,pos):
        self.spritesheet = Spritesheet('blocks')
        self.index = image
        self.image = Spritesheet.getFrames(self, 2, self.index, blockSize, blockSize)
        self.frame = 0
        self.rect = pygame.Rect(0,0,blockSize,blockSize)
        self.rect.topleft = pos

        self.direction = []

    def draw(self):
        self.image = Spritesheet.getFrames(self, 2, self.index, blockSize, blockSize) # Reload the sprite so that the board is accurate
        if self.index > EMPTY:
            screen.blit(self.image[self.frame], self.rect)

class Spritesheet:
    def __init__(self, filename):
        self.spritesheet = pygame.image.load(os.path.join('sprites', 'spr_' + filename + '.png')).convert()

    def getImage(self, x, y, width, height):
        image = pygame.Surface((width, height))
        image.blit(self.spritesheet, (0, 0), (x, y, width, height))
        image.set_colorkey((0,0,0))

        return image

    def getFrames(self, frames, y, width, height):
        frame = 0
        position = y * width # Where the first frame of an animation is on the spritesheet
        framesList = []
        for x in range(frames):
            if x == 0:
                framesList.append(self.spritesheet.getImage(frame, position, width, height))
            else:
                frame += height
                framesList.append(self.spritesheet.getImage(frame, position, width, height))

        return framesList

    def animate(self, state):
        # This is just for hardcoded animation looping and non-looping
        now = pygame.time.get_ticks() / 24
        if self.loop is True:
            if now - self.lastUpdate > 10:
                self.lastUpdate = now
                self.currentFrame = (self.currentFrame + 1) % len(state) # Goes through each frame and loops
                self.image = state[self.currentFrame]
            elif self.currentFrame == len(state) - 1 and state == self.animStates['lose']:
                self.loop = False # Stop looping once on last frame
        else:
            self.currentFrame = len(state)-1
            self.image = state[self.currentFrame]

def drawHealthBar(surf, pos, size, borderC, backC, healthC, progress):
    # Credits to Rabbit76 on stackoverflow
    pygame.draw.rect(surf, backC, (pos, size))
    pygame.draw.rect(surf, borderC, (pos, size), 1)
    innerPos  = (pos[0]+1, pos[1]+1)
    innerSize = ((size[0]-2) * progress, size[1]-2)
    pygame.draw.rect(surf, healthC, (innerPos, innerSize))

class Character(object):
    def __init__(self, gameboard, sprite, coordX, coordY, health):
        self.maxHealth = health
        self.health = self.maxHealth
        self.spclMeter = 0
        self.maxSpclMeter = 10
        self.notHurt = True
        self.isAtk = False # For the enemy
        self.gameboard = gameboard
        # Animation control
        self.currentFrame = 0
        self.lastUpdate = 0
        self.loop = True
        # Get the sprites
        self.spritesheet = Spritesheet(sprite)
        self.loadImages()
        self.image = self.idleFrames[0]
        self.rect = self.image.get_rect()

    def drawBars(self, surf):
        healthRect = pygame.Rect(0, 0, self.image.get_width()/1.5, 10)
        healthRect.midbottom = self.rect.centerx, (self.rect.top - 5)
        spclRect = pygame.Rect(0, 0, self.image.get_width()/2, 5)
        spclRect.midbottom = self.rect.centerx, self.rect.top
        if self.health >= 0.9:
            drawHealthBar(surf, healthRect.topleft, healthRect.size,
                    (0, 0, 0), (0, 0, 0), (0, 255, 0), self.health/self.maxHealth)
        else:
            drawHealthBar(surf, healthRect.topleft, healthRect.size,
                    (0, 0, 0), (0, 0, 0), (0, 0, 0), 0)
        if self.spclMeter > 0:
            drawHealthBar(surf, spclRect.topleft, spclRect.size,
                    (0, 0, 0), (0, 0, 0), (79, 191, 255), self.spclMeter/self.maxSpclMeter)
        else:
            drawHealthBar(surf, spclRect.topleft, spclRect.size,
                    (0, 0, 0), (0, 0, 0), (0, 0, 0), 0)

    def enemyDamageCalc(self, power):
        # Calculate damage AGAINST the ENEMY
        self.notHurt = False
        damageMod = 2
        if gameBoard.canAdd is False:
            damageMod = 1 # Cause less damage when the board can no longer grow
        else:
            damageMod = 2
        extraDamage = random.randint(1,2)
        damage = (((power/50)+damageMod) * extraDamage)
        if self.health >= 0.9:
            self.health -= math.ceil(damage)
        else:
            self.health = 0

    def playerDamageCalc(self, min, max):
        # Calculate damage AGAINST the PLAYER
        gameBoard.player.notHurt = False
        damageMod = 1
        if self.isAtk is True:
            if gameBoard.canAdd is False:
                damageMod = 2 # Cause more damage on player when board can no longer grow
            else:
                damageMod = 1
            power = random.randint(min, max)
            extraDamage = random.randint(1,2)
            damage = (((power/50)+damageMod) * extraDamage)
            time.sleep(0.2) # Sync attack animation with damage
            if gameBoard.player.health >= 0.9:
                gameBoard.player.health -= math.ceil(damage)
            else:
                gameBoard.player.health = 0
            time.sleep(0.8)
            gameBoard.enemyTurn = gameBoard.maxEnemyTurn
            self.isAtk = False

    def enemyAtk(self):
        if gameBoard.player.health >= 0.9:
            self.isAtk = True
            damageTimer = threading.Thread(target=self.playerDamageCalc, args=(gameBoard.minEnemyAtk, gameBoard.maxEnemyAtk))
            damageTimer.start()
        else:
            self.isAtk = False

    def checkHurt(self):
        if self.notHurt is False:
            time.sleep(0.8)
            self.notHurt = True

    def loadImages(self):
        self.idleFrames = Spritesheet.getFrames(self, 2, 0, charSize, charSize)
        self.atkFrames = Spritesheet.getFrames(self, 2, 1, charSize, charSize)
        self.spclFrames = Spritesheet.getFrames(self, 2, 2, charSize, charSize)
        self.hurtFrames = Spritesheet.getFrames(self, 2, 3, charSize, charSize)
        self.loseFrames = Spritesheet.getFrames(self, 2, 4, charSize, charSize)
        self.winFrames = Spritesheet.getFrames(self, 2, 5, charSize, charSize)
        # Keep a list of animation states
        self.animStates = dict(
            idle = self.idleFrames,
            atk = self.atkFrames,
            spcl = self.spclFrames,
            hurt = self.hurtFrames,
            lose = self.loseFrames,
            win = self.winFrames,
        )
        # Default setting
        self.currentAnim = self.animStates['idle']

    def blitme(self, x, y):
        Spritesheet.animate(self, self.currentAnim)
        if self.notHurt is True and gameBoard.state != 'dropping':
            self.currentAnim = self.animStates['idle']
        elif self.notHurt is False and gameBoard.state != 'dropping':
            self.currentAnim = self.animStates['hurt']
            hurtTimer = threading.Thread(target=self.checkHurt) # It took us 3 hours to make this potato salad!! THREE HOURS!!!
            hurtTimer.start()
        if self.health <= 0:
            self.health = 0
            self.currentAnim = self.animStates['lose']
        # Just for the enemy
        if self == gameBoard.enemy:
            Text('slkscr', 15, 'Next:' + str(gameBoard.enemyTurn), (0,0,0), (x + 40), (y - 35))
            if self.isAtk is True:
                self.currentAnim = self.animStates['atk']
        # VICTORY!
        if self == gameBoard.player:
            if gameBoard.enemy.health <= 0:
                self.currentAnim = self.animStates['win']
        self.rect.topleft = (x, y)
        screen.blit(self.image, self.rect)
        # Show health numbers
        Text('slkscr', 10, str(self.health) + '/' + str(self.maxHealth), (0,0,0), (x + 120), (y - 15))
        self.drawBars(screen)

gameBoard = GameBoard(1500, 'charA', 'enemA', 100, 400, 2, 5, 30, 85)
# GameBoard(block generation speed, player character, enemy, player HP, enemy HP, amount of colors to generate,
# player Turns until enemy attacks, minumum damage from enemy, maximum damage from enemy)
CURSOR = Cursor()

# More pygame specific stuff....
while True:
    GameBoard.runGame(gameBoard)
