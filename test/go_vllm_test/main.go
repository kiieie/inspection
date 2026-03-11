package main

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"time"
)

// OpenAI-compatible API Structures
type MessageContent struct {
	Type     string    `json:"type"`
	Text     string    `json:"text,omitempty"`
	ImageURL *ImageURL `json:"image_url,omitempty"`
}

type ImageURL struct {
	URL string `json:"url"`
}

type Message struct {
	Role    string           `json:"role"`
	Content []MessageContent `json:"content"`
}

type ChatPayload struct {
	Model       string    `json:"model"`
	Messages    []Message `json:"messages"`
	Temperature float64   `json:"temperature"`
}

type ChatResponse struct {
	Choices []struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
	} `json:"choices"`
}

func encodeImage(imagePath string) (string, error) {
	data, err := ioutil.ReadFile(imagePath)
	if err != nil {
		return "", err
	}
	return base64.StdEncoding.EncodeToString(data), nil
}

func callVLLM(url, model, prompt, imageB64 string) (string, time.Duration, error) {
	payload := ChatPayload{
		Model: model,
		Messages: []Message{
			{
				Role: "user",
				Content: []MessageContent{
					{Type: "text", Text: prompt},
					{Type: "image_url", ImageURL: &ImageURL{URL: fmt.Sprintf("data:image/jpeg;base64,%s", imageB64)}},
				},
			},
		},
		Temperature: 0.0,
	}

	jsonData, _ := json.Marshal(payload)
	start := time.Now()
	
	resp, err := http.Post(url+"/chat/completions", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return "", 0, err
	}
	defer resp.Body.Close()

	elapsed := time.Since(start)
	body, _ := ioutil.ReadAll(resp.Body)

	var chatResp ChatResponse
	if err := json.Unmarshal(body, &chatResp); err != nil {
		return string(body), elapsed, fmt.Errorf("JSON Parse Error: %v", err)
	}

	if len(chatResp.Choices) > 0 {
		return chatResp.Choices[0].Message.Content, elapsed, nil
	}
	return "No response content", elapsed, nil
}

func main() {
	imagePath := "/home/kiie/projects/python/inspection/test_vlm.jpg" // Sample image
	if _, err := os.Stat(imagePath); os.IsNotExist(err) {
		fmt.Printf("Test image not found at %s. Please provide a sample image.\n", imagePath)
		return
	}

	imageB64, err := encodeImage(imagePath)
	if err != nil {
		fmt.Printf("Image encoding failed: %v\n", err)
		return
	}

	// 1. OCR Test (GLM-OCR)
	fmt.Println("--- [Go] OCR Test (GLM-OCR) ---")
	ocrPrompt := "Extract only the numbers from this digital gauge display."
	ocrResult, ocrTime, err := callVLLM("http://localhost:8000/v1", "unsloth/GLM-OCR", ocrPrompt, imageB64)
	if err != nil {
		fmt.Printf("OCR Error: %v\n", err)
	} else {
		fmt.Printf("Result: %s\nTime: %v\n", ocrResult, ocrTime)
	}

	// 2. Classification & Abnormality Test (Qwen3.5)
	fmt.Println("\n--- [Go] Classification & Abnormality Test (Qwen3.5) ---")
	qwenPrompt := "Analyze this industrial component. Identify: 1) Type (AG/DG/LED/SW/ETC), 2) Status (Normal/Abnormal), 3) Detailed State (e.g. value or on/off)."
	qwenResult, qwenTime, err := callVLLM("http://localhost:8001/v1", "Jackrong/Qwen3.5-9B-Claude-4.6-Opus-Reasoning-Distilled-GGUF", qwenPrompt, imageB64)
	if err != nil {
		fmt.Printf("Qwen Error: %v\n", err)
	} else {
		fmt.Printf("Result: %s\nTime: %v\n", qwenResult, qwenTime)
	}
}
