    if st.session_state.audio_file and os.path.exists(st.session_state.audio_file):
        with open(st.session_state.audio_file, "rb") as audio_file:
            audio_data = audio_file.read()

        audio_base64 = base64.b64encode(audio_data).decode("ascii")
        sentences = split_text_into_sentences(text_to_listen)
        sentences_b64 = base64.b64encode(json.dumps(sentences).encode('utf-8')).decode('ascii')
        full_text_b64 = base64.b64encode(text_to_listen.encode('utf-8')).decode('ascii')
        audio_html = f"""
        <style>
            *{{box-sizing:border-box;}}
            #ttsAudio::-webkit-media-controls-playback-rate-button,
            #ttsAudio::-moz-media-controls-playback-rate-button,
            #ttsAudio::-ms-media-controls-playback-rate-button{{display:none!important;}}

            .ap-card{{
                background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);
                border:1px solid rgba(99,102,241,.25);
                border-radius:20px;
                padding:24px 24px 20px;
                margin-bottom:16px;
                box-shadow:0 8px 32px rgba(0,0,0,.35);
            }}
            .ap-label{{display:flex;align-items:center;gap:10px;margin-bottom:14px;}}
            .ap-dot{{
                width:10px;height:10px;border-radius:50%;
                background:#6366f1;
                animation:ap-pulse 1.6s ease-in-out infinite;
                animation-play-state:paused;
            }}
            @keyframes ap-pulse{{
                0%,100%{{opacity:1;transform:scale(1);}}
                50%{{opacity:.35;transform:scale(1.4);}}
            }}
            .ap-label-text{{
                font-size:.8rem;font-weight:700;letter-spacing:.08em;
                text-transform:uppercase;color:#94a3b8;
            }}
            #ttsAudio{{width:100%;border-radius:12px;outline:none;accent-color:#6366f1;display:block;}}
            .ap-progress-row{{display:flex;align-items:center;gap:10px;margin-top:14px;}}
            .ap-time{{font-size:.78rem;color:#64748b;min-width:36px;font-variant-numeric:tabular-nums;}}
            .ap-bar-wrap{{
                flex:1;height:6px;border-radius:999px;
                background:rgba(255,255,255,.1);overflow:hidden;cursor:pointer;
            }}
            .ap-bar-fill{{
                height:100%;width:0%;border-radius:999px;
                background:linear-gradient(90deg,#6366f1,#a78bfa);
                transition:width .25s linear;
            }}
            .ap-speeds{{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px;}}
            .ap-speed{{
                padding:6px 14px;border-radius:999px;
                border:1.5px solid rgba(255,255,255,.15);
                background:rgba(255,255,255,.04);
                color:#cbd5e1;font-size:.82rem;font-weight:600;cursor:pointer;
                transition:background .18s,border-color .18s,transform .12s;
            }}
            .ap-speed:hover{{background:rgba(255,255,255,.10);transform:translateY(-1px);}}
            .ap-speed.active{{background:rgba(99,102,241,.25);border-color:#6366f1;color:#a5b4fc;}}

            .ap-reading-card{{
                background:rgba(15,23,42,.97);
                border:1px solid rgba(99,102,241,.18);
                border-radius:18px;padding:20px 22px;margin-top:4px;
            }}
            .ap-reading-header{{display:flex;align-items:center;gap:8px;margin-bottom:12px;}}
            .ap-reading-title{{font-size:.9rem;font-weight:700;color:#e2e8f0;letter-spacing:.02em;}}
            .ap-reading-pct{{margin-left:auto;font-size:.78rem;color:#6366f1;font-weight:700;}}
            .ap-read-bar-wrap{{
                height:4px;border-radius:999px;
                background:rgba(255,255,255,.08);margin-bottom:16px;overflow:hidden;
            }}
            .ap-read-bar{{
                height:100%;width:0%;border-radius:999px;
                background:linear-gradient(90deg,#6366f1,#a78bfa);
                transition:width .3s ease;
            }}
            .listen-sentence{{
                display:inline;border-radius:6px;
                transition:background .15s,box-shadow .15s;
                background:transparent;color:#cbd5e1;
                line-height:1.95;font-size:1.05rem;letter-spacing:.01em;
            }}
            .listen-sentence.active{{
                background:rgba(99,102,241,.22);
                box-shadow:0 0 0 2px rgba(99,102,241,.4);
                padding:2px 5px;border-radius:7px;color:#e0e7ff;
            }}
            .listen-sentence.done{{color:#475569;}}
            @media(max-width:640px){{
                .ap-card{{padding:16px;}}
                .listen-sentence{{font-size:.97rem;}}
            }}
        </style>

        <div class="ap-card">
            <div class="ap-label">
                <div class="ap-dot" id="apDot"></div>
                <span class="ap-label-text">Now Playing</span>
            </div>
            <audio id="ttsAudio" controls controlsList="nodownload">
                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mpeg">
                Your browser does not support HTML5 audio.
            </audio>
            <div class="ap-progress-row">
                <span class="ap-time" id="apCur">0:00</span>
                <div class="ap-bar-wrap" id="apBarWrap">
                    <div class="ap-bar-fill" id="apBarFill"></div>
                </div>
                <span class="ap-time" id="apDur">0:00</span>
            </div>
            <div class="ap-speeds" id="apSpeeds"></div>
        </div>

        <div class="ap-reading-card">
            <div class="ap-reading-header">
                <span class="ap-reading-title">&#128214; Reading Progress</span>
                <span class="ap-reading-pct" id="apReadPct">0%</span>
            </div>
            <div class="ap-read-bar-wrap">
                <div class="ap-read-bar" id="apReadBar"></div>
            </div>
            <div id="sentenceContainer" aria-live="polite"></div>
        </div>

        <script>
        (function(){{
            var sentences   = JSON.parse(atob('{sentences_b64}'));
            var audio       = document.getElementById('ttsAudio');
            var dot         = document.getElementById('apDot');
            var barFill     = document.getElementById('apBarFill');
            var curEl       = document.getElementById('apCur');
            var durEl       = document.getElementById('apDur');
            var barWrap     = document.getElementById('apBarWrap');
            var readBar     = document.getElementById('apReadBar');
            var readPct     = document.getElementById('apReadPct');
            var sentBox     = document.getElementById('sentenceContainer');
            var speedsWrap  = document.getElementById('apSpeeds');
            var SPEEDS      = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];
            var timings     = [];
            var activeIdx   = -1;

            function fmt(s){{
                var m=Math.floor(s/60), sec=Math.floor(s%60);
                return m+':'+(sec<10?'0':'')+sec;
            }}

            SPEEDS.forEach(function(sp){{
                var b=document.createElement('button');
                b.className='ap-speed'+(sp===1.0?' active':'');
                b.textContent=sp+'x';
                b.addEventListener('click',function(){{
                    audio.playbackRate=sp;
                    speedsWrap.querySelectorAll('.ap-speed').forEach(function(x){{
                        x.classList.toggle('active',parseFloat(x.textContent)===sp);
                    }});
                }});
                speedsWrap.appendChild(b);
            }});

            var weights=sentences.map(function(s){{return Math.max(1,s.trim().split(/\\s+/).length);}});

            function buildTimings(){{
                timings=[];
                var dur=audio.duration||0; if(!dur) return;
                var tot=weights.reduce(function(a,b){{return a+b;}},0);
                var t=0;
                weights.forEach(function(w){{
                    var len=(w/tot)*dur;
                    timings.push({{start:t,end:Math.min(dur,t+len)}});
                    t+=len;
                }});
            }}

            function renderSentences(){{
                if(!sentences.length){{
                    sentBox.innerHTML='<p style="color:#64748b;margin:0">No sentences found.</p>';
                    return;
                }}
                sentBox.innerHTML='<p style="margin:0;text-align:left;word-wrap:break-word">'+
                    sentences.map(function(s,i){{
                        return '<span class="listen-sentence" data-i="'+i+'">'+s+'</span> ';
                    }}).join('')+'</p>';
            }}

            function tick(){{
                var t=audio.currentTime, dur=audio.duration||1;
                var pct=Math.min(100,(t/dur)*100);
                barFill.style.width=pct+'%';
                readBar.style.width=pct+'%';
                readPct.textContent=Math.round(pct)+'%';
                curEl.textContent=fmt(t);
                durEl.textContent=fmt(audio.duration||0);
                if(!timings.length||!sentences.length) return;
                var idx=timings.findIndex(function(tm){{return t>=tm.start&&t<tm.end;}});
                if(idx===-1) idx=audio.ended?-1:0;
                if(idx!==activeIdx){{
                    activeIdx=idx;
                    sentBox.querySelectorAll('.listen-sentence').forEach(function(el){{
                        var i=Number(el.dataset.i);
                        el.classList.toggle('active',i===idx);
                        el.classList.toggle('done',i<idx);
                        if(i===idx) el.scrollIntoView({{behavior:'smooth',block:'nearest'}});
                    }});
                }}
            }}

            audio.addEventListener('play',  function(){{dot.style.animationPlayState='running';}});
            audio.addEventListener('pause', function(){{dot.style.animationPlayState='paused';}});
            audio.addEventListener('ended', function(){{dot.style.animationPlayState='paused';}});
            barWrap.addEventListener('click',function(e){{
                var r=barWrap.getBoundingClientRect();
                audio.currentTime=((e.clientX-r.left)/r.width)*(audio.duration||0);
            }});
            audio.addEventListener('loadedmetadata',function(){{
                durEl.textContent=fmt(audio.duration);
                buildTimings();
            }});
            audio.addEventListener('timeupdate',tick);
            audio.addEventListener('seeked',tick);
            renderSentences();
        }})();
        </script>
        """

        components.html(audio_html, height=620)

        cols = st.columns(3)
        if cols[0].button("Play Audio", key="audio_play_btn"):
            if st.session_state.get("current_user_id") is not None:
                track_audio_played(user_id=st.session_state.current_user_id, metadata={"mode": "Listen"})
        if cols[1].button("Pause Audio", key="audio_pause_btn"):
            if st.session_state.get("current_user_id") is not None:
                track_audio_paused(user_id=st.session_state.current_user_id, metadata={"mode": "Listen"})
        if cols[2].button("Replay Audio", key="audio_replay_btn"):
            if st.session_state.get("current_user_id") is not None:
                track_audio_replayed(user_id=st.session_state.current_user_id, metadata={"mode": "Listen"})

        st.download_button(
            label="Download Audio",
            data=audio_data,
            file_name="learning_audio.mp3",
            mime="audio/mpeg",
            key="download_audio"
        )
