# This is a liuidsoap script. It starts a tlnet server with 2 commands.
# The telnet server starts or stops the audio stream.
# The audio stream takes the files in a specific directory and sends them to Icecast. 

settings.init.force_start := true
settings.server.telnet.port := 1234
settings.server.telnet := true

# make telnet availible from all addresses (ai talkmaster docker container)
settings.server.telnet.bind_addr := "0.0.0.0"

log.file := true
settings.log.file.path := "/var/log/liquidsoap/server.log"
settings.log.level := 4


streams = ref([])
count = ref(0)


def create_stream(join_key) =
  print("Start streaming #{join_key}")
  if
    list.assoc.mem(join_key, streams())
  then
    print("Stream #{join_key} already exists")
    "Stream for join_key #{join_key} already exists!"
  else
    l = playlog(persistency = "/var/log/liquidsoap/playlog_#{join_key}.txt", hash=fun(m) -> m['initial_uri'])

    def check(r)
      m = request.metadata(r)
      if l.last(m) == infinity then
          true
      else
          false
      end
    end

    def add_track_to_playlog(m)
      # the on_metadata and on_track methods are called during the playing of the audio file m
      if l.last(m) == infinity then
        print("playing #{m['initial_uri']}")
        l.add(m)
      end
    end

    generated_playlist = playlist("/generated-audio/active/#{join_key}", prefetch=1, loop=false, reload=1, reload_mode="seconds", mode="normal", check_next=check)

    generated_playlist.on_metadata(synchronous=true, add_track_to_playlog)
    generated_playlist.on_track(synchronous=true, add_track_to_playlog)

    waiting_playlist = playlist("/fallback-audio/", mode="normal")
    waiting_playlist = amplify(0.6, waiting_playlist)
    waiting_safe = mksafe(waiting_playlist)

    stream_content = fallback(track_sensitive=false, [generated_playlist, waiting_safe])
    out = output.icecast(
        id="restream-#{count()}",
        %mp3(bitrate = 32, samplerate = 22050, stereo = false),
        mount="/stream/#{join_key}",
        host="icecast",
        port=8000,
        password="srcpassword",
        mean(stream_content)
    )
    
    count := count() + 1
    outfile = output.file(
      id="fileoutput-#{count()}",
      %mp3(bitrate = 32, samplerate = 22050, stereo = false),
      "fileoutput-#{join_key}.mp3",
      mean(stream_content)
    )
    count := count() + 1
    streams := [...streams(), (join_key, out.shutdown)]
    "OK!"
  end
end

def delete_stream(join_key) =
  if
    not list.assoc.mem(join_key, streams())
  then
    "Stream for join_key #{join_key} does not exists!"
  else
    print("Stop streaming #{join_key}")
    shutdown = list.assoc(join_key, streams())
    shutdown()
    streams := list.filter((fun (el) -> fst(el) != join_key), streams())
    "OK!"
  end
end

server.register(
  namespace="aitstream",
  description="Start a stream from directory.",
  usage="start <join_key>",
  "start",
  create_stream
)
server.register(
  namespace="aitstream",
  description="Stop a stream from directory.",
  usage="stop <join_key>",
  "stop",
  delete_stream
)