# Issues

## Audio Delay

There is a delay between the file queueing in Liquidsoap (via http from python) and hearing them in the Icecast stream.
This delay is higher for the OpenSimulator viewers compared to other media players (e.g. VLC).
About 16 seconds delay when hearing the audio via VLC.
About 50 seconds delay when hearing the audio via Firestorm Viewer.

The length of the text / audio does not affect this delay.

### Attempted Solutions

disabling burst-on-connect might reduce the delay

https://icecast.org/docs/icecast-2.3.1/config-file.html


Result:

testing showed no improvement when setting burst-on-connect to 0 for listening to the stream on Firestorm



## join_key conflict

What if two users decide to use the same join_key? (unintentionally or by malicious intent)

They would essentially use the same conversation and interfere with each other.

### Possible Solution

- Change join_key to a secret key.
- Introduce a displayname variable
  - Used in name for Icecast URL
  - Used in mp3-Metadata
  
Status:
not implemented yet


