# Bluelight

The main function of this program is to start `moonlight-qt` automatically when it detects that a bluetooth controller is connected. It was most useful for me when I was running a Raspberry Pi Headless. Before this I had to SSH into the pi and run command manually. Now I just turn on my Xbox controller and Moonlight immediately launches.  

When you turn off the controller it will wait a certain amount of time before shutting down `moonlight-qt`. The reason for the delay is just in case your battery dies on you, you have time to change it before moonlight gets shut down. The default time is set to 300 seconds (5 minutes) but you can adjust it using the command `bluelight timeout <seconds>`. 

## Installation
In theory to install it all you need to do is have `pipx` installed with the ability to run the global flag. This requires using a version of `pipx` > 1.6 I believe. But if you have that ready then you can just run 

```bash
sudo pipx install bluelight --global
sudo pipx ensurepath --global
```
then restart the terminal. 

Had to follow this to do the install for pipx
https://github.com/pypa/pipx/issues/754

## Use
You can now run `bluelight pair` to pair your controller and then you can use `bluelight run` to run the program. This will run it in the foreground however and will stop once you close the terminal. So if you want to be always running in the background just run `sudo bluelight daemon-start`. Now whenever you turn on your pi you just have to connect that bluetooth controller and it will start up moonlight.