def test_model_inference(system_setup):
    # 1. 첫 번째 행의 데이터로 테스트
    row = system_setup.df.iloc[0]
    img_path = system_setup.get_latest_image(row['mission_name'], row['inspection_name'])
    
    if img_path:
        print(f"\n[테스트] 추론 시작: {img_path}")
        result = system_setup.run_classifier(img_path)
        
        # 검출된 객체 정보 출력
        print(f"검출된 객체 수: {len(result.boxes)}")
        for box in result.boxes:
            cls_id = int(box.cls[0])
            label = result.names[cls_id]
            conf = box.conf[0]
            print(f" - {label}: {conf:.2f}")
    else:
        pytest.skip("이미지 파일이 없어 추론 테스트를 건너뜁니다.")