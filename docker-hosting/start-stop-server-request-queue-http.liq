# This is a liuidsoap script. It starts a http server with 3 commands.
# The http server starts or stops the audio stream.
# The audio stream takes the files in a specific directory and sends them to Icecast.
# Audio files are queued into the stream by python via http requests.

settings.init.force_start := true

log.file := true
settings.log.file.path := "/var/log/liquidsoap/server.log"
settings.log.level := 4


streams = ref([])
count = ref(0)

queues = ref([])

def start_stream(http_request) =
  join_key = http_request.body()

  if
    list.assoc.mem(join_key, streams())
  then
    print("Stream #{join_key} already exists")
    http.response(
      content_type="text/html",
      data="Stream for join_key #{join_key} already exists!"
    )
  else
    print("Starting stream #{join_key}")
    waiting_playlist = playlist("/fallback-audio/", mode="normal")
    waiting_playlist = mksafe(waiting_playlist)
    waiting_playlist = amplify(0.6, waiting_playlist)
    

    action_queue = request.queue(id="action_queue_#{join_key}")

    # track_sensitive=false means the source can switch during tracks
    stream_content = fallback(track_sensitive=false, [action_queue, waiting_playlist])

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
    queues := [...queues(), (join_key, action_queue)]
    http.response(
      content_type="text/html",
      data="OK!"
    )
  end
end

def stop_stream(http_request) =
  join_key = http_request.body()
  if
    not list.assoc.mem(join_key, streams())
  then
    http.response(
      content_type="text/html",
      data="Stream for join_key #{join_key} does not exists!"
    )
  else
    print("Stop streaming #{join_key}")
    shutdown = list.assoc(join_key, streams())
    shutdown()

    # remove stream and queue with ID join_key
    streams := list.filter((fun (el) -> fst(el) != join_key), streams())
    queues := list.filter((fun (el) -> fst(el) != join_key), queues())
    http.response(
      content_type="text/html",
      data="OK!"
    )
  end
end

def queue_audio(http_request) =
  # we should use json https://www.liquidsoap.info/doc-dev/json.html but it didn't behave as intended here after careful testing
  parts = string.split(separator="::", http_request.body())
  join_key = list.nth(parts, 0)
  filename = list.nth(parts, 1)

  if
    not list.assoc.mem(join_key, streams())
  then
    http.response(
      content_type="text/html",
      data="Stream for join_key #{join_key} does not exists!"
    )
  else
    print("Queuing #{filename} for #{join_key}")
    action_queue = list.assoc(join_key, queues())

    filename_full = "/generated-audio/active/#{join_key}/#{filename}"
    req = request.create(persistent=true, filename_full)
    action_queue.push(req)

    http.response(
      content_type="text/html",
      data="OK!"
    )
  end
end

harbor.http.register.simple(port=8080, method="POST", "/start_stream", start_stream)
harbor.http.register.simple(port=8080, method="POST", "/stop_stream", stop_stream)
harbor.http.register.simple(port=8080, method="POST", "/queue_audio", queue_audio)