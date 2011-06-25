from shinymud.models.player import Player

import threading
import socket

class WebsocketHandler(threading.Thread):
    
    def __init__(self, port, host, world):
        threading.Thread.__init__(self)
        self.world = world
        self.daemon = True # So this thread will exit when the main thread does
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind((host, port))
        self.world.log.info("WebsocketHandler running on host: %s and port: %s." % (host, port))
    
    def run(self):
        """Start the connection-handler thread running.
        This thread will accept connections, create a Player object for the
        player logging in, and then add that Player object to the world.
        """
        # This doesn't actually work - it needs to be implemented!
        # self.listener.listen(5)
        #         self.world.log.debug("Listener started")
        #         while 1:
        #             try:
        #                 new_player = Player(self.listener.accept())
        #             except Exception, e:
        #                 self.world.log.debug(str(e))
        #             else:
        #                 self.set_telnet_options(new_player)
        #                 self.world.log.info("Client logging in from: %s" % str(new_player.addr))
        #                 new_player.conn.setblocking(0)
        #                 # The player_add function in the world requires access to the player_list,
        #                 # which the main thread edits quite a bit -- that's why we need a lock 
        #                 # before we add a player
        #                 self.world.player_list_lock.acquire()
        #                 self.world.player_add(new_player)
        #                 self.world.player_list_lock.release()
    


class TelnetHandler(threading.Thread):
    
    def __init__(self, port, host, world):
        threading.Thread.__init__(self)
        self.world = world
        self.daemon = True # So this thread will exit when the main thread does
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind((host, port))
        self.world.log.info("TelnetHandler running on host: %s and port: %s." % (host, port))
    
    def run(self):
        """Start the connection-handler thread running.
        This thread will accept connections, create a Player object for the
        player logging in, and then add that Player object to the world.
        """
        self.listener.listen(5)
        self.world.log.debug("Listener started")
        while 1:
            try:
                new_player = Player(self.listener.accept())
            except Exception, e:
                self.world.log.debug(str(e))
            else:
                self.set_telnet_options(new_player)
                self.world.log.info("Client logging in from: %s" % str(new_player.addr))
                new_player.conn.setblocking(0)
                # The player_add function in the world requires access to the player_list,
                # which the main thread edits quite a bit -- that's why we need a lock 
                # before we add a player
                self.world.player_list_lock.acquire()
                self.world.player_add(new_player)
                self.world.player_list_lock.release()
    
    def set_telnet_options(self, pc):
        """Petition client to run in linemode and to send window size change
        notifications.
        Some telnet clients, such as putty, start in non-linemode by default
        (they transmit each character as they receive it from the player). We want
        them to switch to linemode in this case, where they transmit each line
        after it's been assembled. We also wan't the client to tell us their
        screen size so we can display things appropriately.
        """
        # IAC + WILL + LINEMODE
        pc.conn.send(chr(255) + chr(251) + chr(34) + '\r\n')
        # We should get a response from their client (immediately)
        pc.conn.settimeout(1.0)
        try:
            result = list(pc.conn.recv(256))
        except socket.timeout:
            # This just means that their telnet client didn't send us a timely
            # response to our initiating linemode... we should just move on
            result = 'Client response FAIL for linemode.'
        finally:
            self.world.log.debug(result)
        
        # IAC DO NAWS (Negotiate About Window Size)
        pc.conn.send(chr(255) + chr(253) + chr(31) + '\r\n')
        try:
            result = list(pc.conn.recv(256))
        except:
            result = 'Client response FAIL for NAWS.'
        else:
            # IAC WILL NAWS
            if result[0:3] == ['\xff', '\xfb', '\x1f']:
                # win, they're willing to do NAWS! Parse their window info
                stuff = ''.join(result[3:])
                pc.parse_winchange(stuff)
        finally:
            pc.conn.settimeout(None)
            self.world.log.debug(str(result))
    


class StatSender(threading.Thread):
    """StatSender is a stand-alone thread that sends game-statistics to any
    client that connects on its port.
     
    When a client connects to StatSender, StatSender sends back a string
    containing a list of players currently logged in and the date the server was
    last restarted, then closes the connection.
     
    NOTE: The host and port that StatSender uses are defined in ShinyMUD's
    config file. This StatSender thread can also be enabled or disabled by
    setting the STATS_ENABLED variable to True or False (respectively) in the
    config file.
     
    The string of game information sent to clients is formatted with each of the
    player's names separated by commas, and the reset date separated from the
    name list by a colon like the following example:
        ResetDate:Player1,Player2,PlayerN
     
    The ResetDate is given as a floating point number expressed in seconds since
    the epoch, in UTC (as returned by Python's time.time() function). See the
    time documentation (http://docs.python.org/library/time.html) for details.
    """
    
    def __init__(self, port, host, world):
        threading.Thread.__init__(self)
        self.daemon = True # So this thread will exit when the main thread does
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind((host, port))
        self.world = world
        self.world.log.info("StatSender running on host: %s and port: %s." % (host, port))
    
    def run(self):
        """Start the StatSender thread running.
        """
        self.listener.listen(5)
        while 1:
            try:
                # Wrap the whole thing in a try block so that if any part of the
                # request causes an exception to be thrown we can just quietly
                # ignore it and it won't crash the server.
                conn, info = self.listener.accept()
                # Send them the game-stats!
                plist = ','.join([name for name in self.world.player_list if isinstance(name, basestring)])
                conn.send(str(self.world.uptime) + ':' + plist)
                conn.close()
            except Exception, e:
                self.world.log.error('StatSender ERROR: ' + str(e))
    


