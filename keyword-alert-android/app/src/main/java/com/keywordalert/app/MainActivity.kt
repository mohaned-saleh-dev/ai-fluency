package com.keywordalert.app

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.keywordalert.app.databinding.ActivityMainBinding

/**
 * Uses the system speech recognizer (often the same backend as Chrome).
 * Vibration and continuous restarts are typically more reliable than a browser tab.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private var speech: SpeechRecognizer? = null
    private var listening = false
    private val mainHandler = Handler(Looper.getMainLooper())
    private var lastTriggerAt = 0L

    private val phoneticWords: Set<String> by lazy {
        buildSet {
            addAll(
                listOf(
                    "bot", "chatbot", "boss", "both", "bought", "bout", "bots", "boat", "bolt", "bat",
                    "butt", "bass", "abbot", "jackpot", "chatbox", "chatbots", "chatpot", "chadbot",
                    "chartbot", "robot", "mascot", "talbot", "sabot", "plot", "slot", "shot", "spot",
                    "squat", "thought", "watt", "yacht", "batch", "botch", "bork", "botal", "boto",
                    "brat", "clot", "colt", "dolt", "fought", "gambit", "hobbit", "insult", "pilot",
                    "punt", "rot", "scot", "shatbot", "swat", "tarot", "trot", "vault", "whirl",
                    "yelp", "fatbot", "batbot", "shadbot", "sandbot", "chatboat", "crabot"
                )
            )
        }
    }

    private val audioPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { ok ->
        if (ok) startSession() else binding.status.text = "Microphone permission denied"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnStart.setOnClickListener {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED
            ) {
                audioPermission.launch(Manifest.permission.RECORD_AUDIO)
            } else {
                startSession()
            }
        }
        binding.btnStop.setOnClickListener { stopSession() }
    }

    private fun startSession() {
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            binding.status.text = "Speech recognition not available on this device"
            return
        }
        listening = true
        binding.status.text = "Listening…"
        speech?.destroy()
        speech = SpeechRecognizer.createSpeechRecognizer(this).also { sr ->
            sr.setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(params: Bundle?) {}
                override fun onBeginningOfSpeech() {}
                override fun onRmsChanged(rmsdB: Float) {}
                override fun onBufferReceived(buffer: ByteArray?) {}
                override fun onEndOfSpeech() {}
                override fun onError(error: Int) {
                    if (listening) {
                        binding.status.text = "Reconnecting… ($error)"
                        mainHandler.postDelayed({ loopListen() }, 350)
                    }
                }

                override fun onResults(results: Bundle?) {
                    handleBundle(results)
                    if (listening) loopListen()
                }

                override fun onPartialResults(partialResults: Bundle?) {
                    handleBundle(partialResults)
                }

                override fun onEvent(eventType: Int, params: Bundle?) {}
            })
        }
        loopListen()
    }

    private fun loopListen() {
        if (!listening) return
        val intent = android.content.Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "en-US")
        }
        try {
            speech?.startListening(intent)
        } catch (_: Exception) {
            mainHandler.postDelayed({ loopListen() }, 400)
        }
    }

    private fun handleBundle(bundle: Bundle?) {
        val list = bundle?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION) ?: return
        for (phrase in list) {
            if (!hasTrigger(phrase)) continue
            val now = android.os.SystemClock.elapsedRealtime()
            if (now - lastTriggerAt < 120) continue
            lastTriggerAt = now
            binding.log.append("\nTrigger: $phrase")
            vibrateBurst()
            flashScreen()
            break
        }
    }

    private fun hasTrigger(text: String): Boolean {
        val t = text.lowercase()
        if (Regex("""\b(bot|chatbot)\b""").containsMatchIn(t)) return true
        val words = Regex("""[a-z0-9']+""").findAll(t).map { it.value }.toList()
        for (w in words) {
            if (w in phoneticWords) return true
            if (w.length >= 4 && w.endsWith("bot")) return true
        }
        return false
    }

    private fun vibrateBurst() {
        val v = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val vm = getSystemService(VIBRATOR_MANAGER_SERVICE) as VibratorManager
            vm.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            getSystemService(VIBRATOR_SERVICE) as Vibrator
        }
        val pattern = longArrayOf(0, 55, 45, 55, 45, 55, 45, 55, 45, 55)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            v.vibrate(VibrationEffect.createWaveform(pattern, -1))
        } else {
            @Suppress("DEPRECATION")
            v.vibrate(pattern, -1)
        }
    }

    private fun flashScreen() {
        val v = binding.root
        val prev = v.background
        v.setBackgroundColor(Color.parseColor("#fffef5"))
        mainHandler.postDelayed({
            v.background = prev
        }, 120)
    }

    private fun stopSession() {
        listening = false
        try {
            speech?.stopListening()
            speech?.cancel()
            speech?.destroy()
        } catch (_: Exception) {
        }
        speech = null
        binding.status.text = "Stopped"
    }

    override fun onDestroy() {
        stopSession()
        super.onDestroy()
    }
}
